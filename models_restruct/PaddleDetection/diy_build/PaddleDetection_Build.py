# encoding: utf-8
"""
自定义环境准备
"""

import os
import sys
import logging
import tarfile
import argparse
import subprocess
import platform
import numpy as np
import yaml
import wget
from Model_Build import Model_Build

logger = logging.getLogger("ce")


class PaddleDetection_Build(Model_Build):
    """
    自定义环境准备
    """

    def __init__(self, args):
        """
        初始化变量
        """
        self.paddle_whl = args.paddle_whl
        self.get_repo = args.get_repo
        self.branch = args.branch
        self.system = args.system
        self.set_cuda = args.set_cuda
        self.dataset_org = args.dataset_org
        self.dataset_target = args.dataset_target

        self.REPO_PATH = os.path.join(os.getcwd(), args.reponame)  # 所有和yaml相关的变量与此拼接
        self.reponame = args.reponame
        self.models_list = args.models_list
        self.models_file = args.models_file
        self.detection_model_list = []
        if str(self.models_list) != "None":
            for line in self.models_list.split(","):
                if ".yaml" in line:
                    self.detection_model_list.append(line.strip().replace("-", "/"))
        elif str(self.models_file) != "None":  # 获取要执行的yaml文件列表
            for file_name in self.models_file.split(","):
                for line in open(file_name):
                    if ".yaml" in line:
                        self.detection_model_list.append(line.strip().replace("-", "/"))
        else:
            for file_name in os.listdir("cases"):
                if ".yaml" in file_name:
                    self.detection_model_list.append(file_name.strip().replace("-", "/"))

    def build_paddledetection(self):
        """
        安装依赖包
        """
        path_now = os.getcwd()
        os.chdir(self.reponame)
        path_repo = os.getcwd()
        os.system("python -m pip install --upgrade pip --ignore-installed")
        os.system("pip install Cython --ignore-installed")
        logger.info("***start setuptools update")
        os.system("pip uninstall setuptools -y")
        os.system("pip install setuptools --ignore-installed")
        os.system("pip install -r requirements.txt --ignore-installed")
        os.system("pip install cython_bbox --ignore-installed")
        os.system("pip install zip --ignore-installed")
        os.system("rpm --import http://li.nux.ro/download/nux/RPM-GPG-KEY-nux.ro")
        os.system("rpm -Uvh http://li.nux.ro/download/nux/dextop/el7/x86_64/nux-dextop-release-0-5.el7.nux.noarch.rpm")
        os.system("yum install ffmpeg ffmpeg-devel -y")
        os.system("apt-get update")
        os.system("apt-get install ffmpeg -y")
        # set sed
        if os.path.exists("C:/Program Files/Git/usr/bin/sed.exe"):
            os.environ["sed"] = "C:/Program Files/Git/usr/bin/sed.exe"
            cmd_weight = (
                '{} -i "s#~/.cache/paddle/weights#D:/ce_data/paddledetection'
                '/det_pretrained#g" ppdet/utils/download.py'.format(os.getenv("sed"))
            )
            subprocess.run(cmd_weight)
        else:
            os.environ["sed"] = "sed"
        # get video
        wget.download("https://paddle-qa.bj.bcebos.com/PaddleDetection/test_demo.mp4")
        # avoid hang in yolox
        cmd = '{} -i "s|norm_type: sync_bn|norm_type: bn|g" configs/yolox/_base_/yolox_cspdarknet.yml'.format(
            os.getenv("sed")
        )
        if platform.system() == "Windows":
            subprocess.run(cmd)
        else:
            subprocess.run(cmd, shell=True)
        # use small data
        cmd_voc = '{} -i "s/trainval.txt/test.txt/g" configs/datasets/voc.yml'.format(os.getenv("sed"))
        if platform.system() == "Windows":
            subprocess.run(cmd_voc)
        else:
            subprocess.run(cmd_voc, shell=True)
        cmd_iter1 = (
            '{} -i "/for step_id, data in enumerate(self.loader):/i\\            max_step_id'
            '=1" ppdet/engine/trainer.py'.format(os.getenv("sed"))
        )
        cmd_iter2 = (
            '{} -i "/for step_id, data in enumerate(self.loader):/a\\                if step_id == '
            'max_step_id: break" ppdet/engine/trainer.py'.format(os.getenv("sed"))
        )
        if platform.system() == "Windows":
            subprocess.run(cmd_iter1)
            subprocess.run(cmd_iter2)
        else:
            subprocess.run(cmd_iter1, shell=True)
            subprocess.run(cmd_iter2, shell=True)
        cmd_mot1 = '{} -i "/for seq in seqs/for seq in [seqs[0]]/g" ppdet/engine/tracker.py'.format(os.getenv("sed"))
        cmd_mot2 = (
            '{} -i "/for step_id, data in enumerate(dataloader):/i\\        '
            'max_step_id=1" ppdet/engine/tracker.py'.format(os.getenv("sed"))
        )
        cmd_mot3 = (
            '{} -i "/for step_id, data in enumerate(dataloader):/a\\            if step_id == '
            'max_step_id: break" ppdet/engine/tracker.py'.format(os.getenv("sed"))
        )
        if platform.system() == "Windows":
            subprocess.run(cmd_mot1)
            subprocess.run(cmd_mot2)
            subprocess.run(cmd_mot3)
        else:
            subprocess.run(cmd_mot1, shell=True)
            subprocess.run(cmd_mot2, shell=True)
            subprocess.run(cmd_mot3, shell=True)
        # compile op
        os.system("python ppdet/ext_op/setup.py install")
        if os.path.exists("/root/.cache/paddle/weights"):
            os.system("rm -rf /root/.cache/paddle/weights")
        os.system("ln -s {}/data/ppdet_pretrained /root/.cache/paddle/weights".format("/ssd2/ce_data/PaddleDetection"))
        # dataset
        os.chdir("dataset")
        if os.path.exists("coco"):
            os.system("rm -rf coco")
        logger.info("***start download data")
        wget.download("https://paddle-qa.bj.bcebos.com/PaddleDetection/coco.zip")
        os.system("unzip coco.zip")
        wget.download("https://paddle-qa.bj.bcebos.com/PaddleDetection/dota.zip")
        os.system("unzip dota.zip")
        wget.download("https://paddle-qa.bj.bcebos.com/PaddleDetection/dota_ms.zip")
        os.system("unzip dota_ms.zip")
        wget.download("https://paddle-qa.bj.bcebos.com/PaddleDetection/mot.zip")
        os.system("unzip mot.zip")
        wget.download("https://paddle-qa.bj.bcebos.com/PaddleDetection/visdrone.zip")
        os.system("unzip visdrone.zip")
        wget.download("https://paddle-qa.bj.bcebos.com/PaddleDetection/VisDrone2019_coco.zip")
        os.system("unzip VisDrone2019_coco.zip")
        # wget.download("https://paddle-qa.bj.bcebos.com/PaddleDetection/mainbody.zip")
        # os.system("unzip mainbody.zip")
        wget.download("https://paddle-qa.bj.bcebos.com/PaddleDetection/voc.zip")
        os.system("unzip voc.zip")
        # wget.download("https://paddle-qa.bj.bcebos.com/PaddleDetection/aic_coco_train_cocoformat.json")
        logger.info("***download data ended")
        # compile cpp
        os.chdir(path_repo + "/deploy/cpp")
        wget.download(
            "https://paddle-qa.bj.bcebos.com/paddle-pipeline/Release-GpuAll-Centos"
            "-Gcc82-Cuda102-Cudnn76-Trt6018-Py38-Compile/latest/paddle_inference.tgz"
        )
        os.system("tar xvf paddle_inference.tgz")
        os.system('sed -i "s|WITH_GPU=OFF|WITH_GPU=ON|g" scripts/build.sh')
        os.system('sed -i "s|CUDA_LIB=/path/to/cuda/lib|CUDA_LIB=/usr/local/cuda/lib64|g" scripts/build.sh')
        os.system('sed -i "s|/path/to/paddle_inference|../paddle_inference|g" scripts/build.sh')
        os.system('sed -i "s|CUDNN_LIB=/path/to/cudnn/lib|CUDNN_LIB=/usr/lib/x86_64-linux-gnu|g" scripts/build.sh')
        os.system("sh scripts/build.sh")
        os.chdir(path_now)
        return 0

    def build_env(self):
        """
        使用父类实现好的能力
        """
        super(PaddleDetection_Build, self).build_env()
        ret = 0
        ret = self.build_paddledetection()
        if ret:
            logger.info("build env failed")
            return ret
        return ret


if __name__ == "__main__":

    def parse_args():
        """
        接收和解析命令传入的参数
            最好尽可能减少输入给一些默认参数就能跑的示例!
        """
        parser = argparse.ArgumentParser("Tool for running CE task")
        parser.add_argument("--models_file", help="模型列表文件", type=str, default=None)
        parser.add_argument("--reponame", help="输入repo", type=str, default=None)
        args = parser.parse_args()
        return args

    args = parse_args()
    print("args:{}".format(args))
    # logger.info('###args {}'.format(args.models_file))
    model = PaddleDetection_Build(args)
    model.build_paddledetection()
