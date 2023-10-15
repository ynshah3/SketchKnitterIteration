import argparse
import os
import torch

from sketch_diffusion import dist_util, logger
from sketch_diffusion.image_datasets import load_data
from sketch_diffusion.resample import create_named_schedule_sampler
from sketch_diffusion.script_util import (
    model_and_diffusion_defaults,
    create_model_and_diffusion,  # you can change mode here
    args_to_dict,
    add_dict_to_argparser,
)
from sketch_diffusion.train_util import TrainLoop


def main():
    args = create_argparser().parse_args()
    print(args)

    if not os.path.exists(args.log_dir):
        os.makedirs(args.log_dir)
    if not os.path.exists(args.data_dir):
        raise FileNotFoundError("The dataset path {args.data_dir} is not found!")

    logger.configure(args.log_dir)

    logger.log("creating model and diffusion...")
    model, diffusion = create_model_and_diffusion(  # you can change mode here
        **args_to_dict(args, model_and_diffusion_defaults().keys())
    )

    model.to(dist_util.dev())
    schedule_sampler = create_named_schedule_sampler(args.schedule_sampler, diffusion)

    logger.log("creating data loader...")
    data = load_data(
        data_dir=args.data_dir,
        batch_size=args.batch_size,
        image_size=args.image_size,
        category=["shoe.npz", ],  # all category names to be trained on
        class_cond=False,
    )

    logger.log("training...")
    TrainLoop(
        model=model,
        diffusion=diffusion,
        data=data,
        batch_size=args.batch_size,
        microbatch=args.microbatch,
        lr=args.lr,
        ema_rate=args.ema_rate,
        log_interval=args.log_interval,
        save_interval=args.save_interval,
        resume_checkpoint=args.resume_checkpoint,
        use_fp16=args.use_fp16,
        fp16_scale_growth=args.fp16_scale_growth,
        schedule_sampler=schedule_sampler,
        weight_decay=args.weight_decay,
        lr_anneal_steps=args.lr_anneal_steps,
    ).run_loop()


def create_argparser():
    defaults = dict(
        data_dir="",
        schedule_sampler="uniform",
        lr=1e-4,
        weight_decay=0.0,
        lr_anneal_steps=0,
        batch_size=4,
        microbatch=-1,  
        ema_rate="0.9999",  
        log_interval=10,
        save_interval=100000,
        resume_checkpoint="",
        use_fp16=False,
        fp16_scale_growth=1e-3,
        log_dir='./logs',
    )
    defaults.update(model_and_diffusion_defaults())
    parser = argparse.ArgumentParser()
    add_dict_to_argparser(parser, defaults)
    return parser


if __name__ == "__main__":
    main()
