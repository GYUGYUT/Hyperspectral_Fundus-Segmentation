import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import random
import torch.nn.functional as F
from pickle import TRUE
from dataloader_dir2 import *
from getmodel  import *
from tqdm import tqdm
from paser_args import *
from pytorchtools import EarlyStopping
from train_test_module import * 
import wandb
from torch.optim.lr_scheduler import StepLR
import segmentation_models_pytorch as smp
def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

# 시드 설정
seed = 42
set_seed(seed)
os.environ["CUDA_DEVICE_ORDER"] = 'PCI_BUS_ID'
os.environ["CUDA_VISIBLE_DEVICES"]= "1,3"  # Set the GPU 0 to use

def run():
    
    
    model = getModel(args.arch, cfg["num_class"])

    # Initialize the model weights using Xavier initialization    
    print("선정된 모델",args.arch)
    check_GPU_STATE = 0
    if torch.cuda.device_count() > 1:
        print("Let's use", torch.cuda.device_count(), "GPUs!")
        check_GPU_STATE  = 2
        model = nn.DataParallel(model,device_ids=[0,1])
    else:
        check_GPU_STATE  = 1
        print("Let's use", torch.cuda.device_count(), "GPUs!")    
    model.to(device)
    early_stopping = EarlyStopping(cfg = cfg)
    loss_fn = smp.losses.JaccardLoss("binary").to(device)
    optimizer = optim.Adam(model.parameters(), lr=cfg["lr"],betas=(0.9, 0.999))
    
    
    wandb.init(
        # set the wandb project where this run will be logged
        project="fundus_hyperspectral_segementation_final3_1024",
        entity = "alswo740012"
    )
    wandb.run.name = str("sigmoid_Hyper_31_mobilev2_") + str(args.arch) + "_" + str(cfg["lr"]) + "_" + str(cfg["batch_size"]) + "_" + str(cfg["imgsize"]) + "_" + str(cfg["num_class"]) 
    wandb.run.save()
    config = {"lr":cfg["lr"],"batch_size":cfg["batch_size"],"architecture" : model}
    wandb.init(config = config)
    wandb.watch(model,loss_fn,log="all",log_freq=10)

    train_data_path = r"/home/msl2024a/resize_idrid2_1024/hyper/hyperspectral_train"
    test_data_path = r"/home/msl2024a/resize_idrid2_1024/hyper/hyperspectral_test"

    Label_train_data_path = r"/home/msl2024a/resize_idrid2/gt/train"
    Label_test_data_path = r"/home/msl2024a/resize_idrid2/gt/test"

    train_data,val_data,test_data = get_loder_main(train_data_path,test_data_path,
                                                   Label_train_data_path,Label_test_data_path,
                                                   cfg["imgsize"],cfg["batch_size"],cfg["shuffle"],cfg["numworks"])
    
    #scheduler setting
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, cfg["epoch"], eta_min=1e-6)

    print( train_data )
    print( val_data )
    print( test_data )

    for epoch in tqdm(range(1,cfg["epoch"]+1),"전체 진행률"):
        train(device,args,model,train_data,val_data,loss_fn, optimizer, epoch,wandb,early_stopping)
        scheduler.step()
        if(early_stopping.early_stop):
            del train_data 
            del val_data
            break
        else:
            pass

    
    test(device,args, model, test_data,loss_fn,wandb,early_stopping, check_GPU_STATE)


#hyper param

 
# script = ['densenet121','resnet50','alexnet','resnext50','mobilenet_v2','densenet169','resnet101','vgg19','resnext101'] # 'vgg16'
script = ['Linknet','UNet++','MAnet','PSPNet','DeepLabV3','DeepLabV3Plus','UNet','FPN'] # 'PAN',
batch_sizes = [1]
for i in script:
    for select_batch in batch_sizes:
        #DEVICE
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = None
        cfg = { model : i,
                    "epoch" : 200,
                    "lr" : 0.0005,
                    "batch_size": select_batch,
                    "shuffle" : TRUE,
                    "imgsize" : [1024,1024],
                    "num_class" : 5,
                    "numworks" : 16,
                    "patience" : 20,
                    "class_name" : ["MA","HM","HE","SE","OD"]}
        args = parse_args(cfg[model],cfg["class_name"])
        a = run()
        del a