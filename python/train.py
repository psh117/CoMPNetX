#!/usr/bin/env python3
import argparse
import datetime
import os
import shutil
from typing import Tuple

import torch
import yaml
import h5py
from torch import nn, optim
from torch.nn import functional as F
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm, trange

from data import CoMPNetXDataset, load_test_data
from models import EnetConstraint, PNet, VoxelEncoder


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--env', type=str, choices=("kitchen", "bartender"), default="bartender", help="which environment to train")
    parser.add_argument('--use_text', action="store_true", help="use text embedding or NTP embedding for constraint representation")
    parser.add_argument('--use_reach', action="store_true", help="add reach path to training dataset")
    parser.add_argument('--use_tsr', action="store_true", help="predict virtual TSR config along with manipulator config")

    # Model parameters
    parser.add_argument('--outsz_enet', type=int, default=256, help='dimension of ENets output vector')
    parser.add_argument('--outsz_constraint', type=int, default=128, help='dimension of ENetConstaint output vector')

    # training parameters
    parser.add_argument('--num_epochs', type=int, default=400)
    parser.add_argument('--checkpoint_step', type=int, default=10, help='step size for saving trained models')
    parser.add_argument('--batch_size', type=int, default=256)
    parser.add_argument('--lr', type=float, default=0.0001)

    # utils
    parser.add_argument('--output_dir', type=str, default='./data/experiments/', help='where to save all the output files')
    parser.add_argument('--use_cuda', action="store_true", help="use CUDA for faster training")
    parser.add_argument('--overwrite', action="store_true", help="ignore existing files in the output directory")

    return parser.parse_args()


def process_args(args: argparse.Namespace) -> argparse.Namespace:
    args.insz_enet = 32 if args.env == "kitchen" else 33
    args.insz_constraint = 4096 if args.use_text else 270
    args.outsz_pnet = 13 if args.use_tsr else 7
    args.insz_pnet = args.outsz_pnet * 2 + args.outsz_enet + args.outsz_constraint
    args.device = "cuda" if torch.cuda.is_available() and args.use_cuda else "cpu"
    args.training_time = datetime.datetime.now()

    if os.path.exists(args.output_dir) and not args.overwrite:
        overwrite = input("{} already exists. Overwrite? [y/N]".format(args.output_dir))
        if overwrite != "y":
            print("\033[91mNot overwriting - exiting. \033[0m")
            exit()

    args.tensorboard_dir = os.path.join(args.output_dir, "tensorboard")
    args.weight_dir = os.path.join(args.output_dir, "model_weight")
    args.torchscript_dir = os.path.join(args.output_dir, "torchscript")
    args.embedding_dir = os.path.join(args.output_dir, "embedding")
    args.script_dir = os.path.join(args.output_dir, "script")

    return args


def prepare_directories(args: argparse.Namespace):
    shutil.rmtree(args.output_dir, ignore_errors=True)
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.tensorboard_dir, exist_ok=True)
    os.makedirs(args.weight_dir, exist_ok=True)
    os.makedirs(args.torchscript_dir, exist_ok=True)
    os.makedirs(args.embedding_dir, exist_ok=True)
    os.makedirs(args.script_dir, exist_ok=True)
    with open(os.path.join(args.output_dir, "args.yaml"), "w") as f:
        yaml.dump(args.__dict__, f)

    dir_path = os.path.dirname(os.path.realpath(__file__))
    for filename in ("train.py", "data.py", "models.py"):
        shutil.copyfile(os.path.join(dir_path, filename), os.path.join(args.script_dir, filename))


def train(args: argparse.Namespace) -> Tuple[nn.Module, nn.Module, nn.Module, optim.Optimizer]:
    # models
    enet = VoxelEncoder(args.insz_enet, args.outsz_enet).to(args.device)
    enet_constraint = EnetConstraint(args.insz_constraint, args.outsz_constraint).to(args.device)
    pnet = PNet(args.insz_pnet, args.outsz_pnet).to(args.device)
    # dataset
    dataset = CoMPNetXDataset(env=args.env, use_text=args.use_text, use_reach=args.use_reach, use_tsr_config=args.use_tsr, use_manifold_distance=False)
    dataloader = DataLoader(dataset, args.batch_size, shuffle=True, drop_last=True)
    # optimizer
    optimizer = torch.optim.Adagrad(list(enet.parameters())+list(enet_constraint.parameters())+list(pnet.parameters()))
    # utils
    writer = SummaryWriter(args.tensorboard_dir)

    # Train the models
    for epoch in trange(args.num_epochs, desc="Epoch"):
        for (inputs, outputs, voxels, task_embeddings) in tqdm(dataloader, leave=False):
            inputs = inputs.to(args.device)
            outputs = outputs.to(args.device)
            voxels = voxels.to(args.device)
            task_embeddings = task_embeddings.to(args.device)
            # forward
            Z_c = enet_constraint.forward(task_embeddings)
            Z_o = enet.forward(voxels)
            predicts = pnet.forward(torch.cat((Z_o, Z_c, inputs), 1))
            # backward
            loss = F.mse_loss(predicts, outputs)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        writer.add_scalar("loss", loss, epoch)
        # Save the models
        if epoch % args.checkpoint_step == 0:
            torch.save(enet.state_dict(), os.path.join(args.weight_dir, "enet_{}.pkl".format(epoch)))
            torch.save(pnet.state_dict(), os.path.join(args.weight_dir, "pnet_{}.pkl".format(epoch)))
            torch.save(enet_constraint.state_dict(), os.path.join(args.weight_dir, "enet_constraint_{}.pkl".format(epoch)))

    writer.close()
    return enet, enet_constraint, pnet, optimizer


def export(args, enet: nn.Module, enet_constraint: nn.Module, pnet: nn.Module):
    # export torchscript
    pnet_script = torch.jit.script(pnet)
    pnet_script.save(os.path.join(args.torchscript_dir, "pnet.pt"))

    # export intermediate embeddings
    data = load_test_data(args.env, args.use_text)
    # voxel
    voxel_data = data["voxel"]
    f = h5py.File(os.path.join(args.embedding_dir, "voxel.hdf5"), "w")
    with torch.no_grad():
        for (scene_name, scene_data) in voxel_data.items():
            g = f.create_group(scene_name)
            for (obj_name, obj_data) in scene_data.items():
                obj_data = obj_data.unsqueeze(0).cuda()
                embedded_data = enet.forward(obj_data)
                g.create_dataset(obj_name, data=embedded_data.cpu().numpy())
    f.close()
    # task embedding
    embedding_data = data["task_embedding"]
    f = h5py.File(os.path.join(args.embedding_dir, "task_embedding.hdf5"), "w")
    with torch.no_grad():
        for (scene_name, scene_data) in embedding_data.items():
            g = f.create_group(scene_name)
            for (obj_name, obj_data) in scene_data.items():
                obj_data = obj_data.unsqueeze(0).cuda()
                embedded_data = enet_constraint.forward(obj_data)
                g.create_dataset(obj_name, data=embedded_data.cpu().numpy())
    f.close()


if __name__ == '__main__':
    args = process_args(get_args())
    # prepare_directories(args)
    # enet, enet_constraint, pnet, optimizer = train(args)

    enet = VoxelEncoder(args.insz_enet, args.outsz_enet)
    enet_constraint = EnetConstraint(args.insz_constraint, args.outsz_constraint)
    pnet = PNet(args.insz_pnet, args.outsz_pnet)
    enet.load_state_dict(torch.load(os.path.join(args.weight_dir, "enet_390.pkl")))
    enet_constraint.load_state_dict(torch.load(os.path.join(args.weight_dir, "enet_constraint_390.pkl")))
    pnet.load_state_dict(torch.load(os.path.join(args.weight_dir, "pnet_390.pkl")))
    enet = enet.cuda()
    enet_constraint = enet_constraint.cuda()
    pnet = pnet.cuda()
    export(args, enet, enet_constraint, pnet)
