#!/usr/bin/env python3

"""vtools-opencv.py module description.

Runs an opencv video filter.
"""
# https://docs.opencv.org/3.4/dd/d43/tutorial_py_video_display.html
# https://docs.opencv.org/3.1.0/d7/d9e/tutorial_video_write.html


import cv2
import math
import numpy as np
import pandas as pd
import sys

PSNR_K = math.log10(2**8 - 1)


def calculate_diff_mse(img, prev_img):
    if prev_img is None:
        return (np.nan, np.nan, np.nan)
    # YCbCr diff**2 / (width*height)
    yuvimg = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    yuvprev_img = cv2.cvtColor(prev_img, cv2.COLOR_BGR2YCrCb)
    diff = yuvimg.astype(np.double) - yuvprev_img.astype(np.double)
    diff_mse = (diff**2).mean(axis=(1, 0))
    return list(diff_mse)


def run_opencv_analysis(infile, add_mse, mse_delta, debug):
    # open the input
    # use "0" to capture from the camera
    video_capture = cv2.VideoCapture(infile)
    if not video_capture.isOpened():
        print(f"error: {infile = } is not open")
        sys.exit(-1)
    width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    size = (width, height)
    fourcc_input = int(video_capture.get(cv2.CAP_PROP_FOURCC))
    fps = video_capture.get(cv2.CAP_PROP_FPS)
    if debug > 0:
        print(f"input: {infile = } {size = } {fourcc_input = } {fps = }")

    # get the tuple keys
    opencv_keys = ["frame_num", "timestamp_ms", "delta_timestamp_ms"]
    if add_mse:
        opencv_keys += [
            "log10_msey",
            "psnr_y",
            "diff_msey",
            "diff_msey_delta_timestamp_ms",
            "diff_mseu",
            "diff_msev",
        ]
        prev_mse_timestamp_ms = np.nan
    df = pd.DataFrame(columns=opencv_keys)

    # process the input
    opencv_vals = []
    prev_timestamp_ms = np.nan
    prev_img = None
    frame_num = 0
    while True:
        # get image
        ret, img = video_capture.read()
        if not ret:
            break
        # process image
        vals = [
            frame_num,
        ]
        # get timestamps
        timestamp_ms = video_capture.get(cv2.CAP_PROP_POS_MSEC)
        if prev_timestamp_ms == np.nan:
            delta_timestamp_ms = np.nan
        else:
            delta_timestamp_ms = timestamp_ms - prev_timestamp_ms
        vals += [timestamp_ms, delta_timestamp_ms]
        if add_mse:
            # get mse
            diff_msey, diff_mseu, diff_msev = calculate_diff_mse(img, prev_img)
            if diff_msey is np.nan:
                log10_msey = np.nan
                psnr_y = np.nan
            else:
                log10_msey = math.log10(diff_msey) if diff_msey != 0.0 else -np.inf

                psnr_y = (
                    np.inf if (log10_msey == -np.inf) else 20 * PSNR_K - 10 * log10_msey
                )
            diff_msey_delta_timestamp_ms = np.nan
            if diff_msey < mse_delta:
                if prev_mse_timestamp_ms != np.nan:
                    diff_msey_delta_timestamp_ms = timestamp_ms - prev_mse_timestamp_ms
                prev_mse_timestamp_ms = timestamp_ms
            vals += [
                log10_msey,
                psnr_y,
                diff_msey,
                diff_msey_delta_timestamp_ms,
                diff_mseu,
                diff_msev,
            ]
        df.loc[len(df.index)] = vals
        # update previous info
        prev_timestamp_ms = timestamp_ms
        prev_img = img
        frame_num += 1

    # release the video objects
    video_capture.release()

    return df
