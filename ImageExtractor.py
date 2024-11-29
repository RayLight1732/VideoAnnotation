import sys
import cv2
import os
import json
from enum import Enum
import time
class Condition(Enum):
    INVALID = 0
    SAFE = 1
    DANGER = 2

def getDepth(annotation:dict,time:float,depth = 0):
    if annotation["start"] <= time <= annotation["end"]:
        for child in annotation["children"]:
            child_depth = getDepth(child,time,depth+1)
            if child_depth != None:
                return child_depth
        return depth
    else:
        return None
    
def isInValidArea(annotation:dict,time:float):
    for child in annotation["children"]:
        if child["start"] <= time <= child["end"]:
            return True
    return False

def getNeraresValidAreaStartTime(annotation:dict,time:float)->float|None:
    children = sorted(annotation["children"],key=lambda child:child["start"])
    for child in children:
        start_time = child["start"]
        if time <=start_time:
            return start_time
    return None

def getCondition(annotation:dict,time):
    depth = getDepth(annotation,time)
    if depth == 1:
        return Condition.SAFE
    elif depth == 2:
        return Condition.DANGER
    else:
        return Condition.INVALID


def saveImage(frame,parent,name):
    start_exec_time = time.time()
    cv2.imwrite(os.path.join(parent,name),frame)
    print(f"{time.time()-start_exec_time:.2f}")

def print_progress_bar(current, total, bar_length=50):
    """
    ステータスバーを表示する関数
    :param current: 現在の進捗値
    :param total: 総進捗値
    :param bar_length: ステータスバーの長さ
    """
    progress = current / total
    block = int(bar_length * progress)
    bar = f"[{'#' * block}{'-' * (bar_length - block)}] {progress * 100:.2f}%"
    sys.stdout.write(f"\r{bar}")
    sys.stdout.flush()

def extractImage(video_path,output_path,fps):
    if video_path != None and output_path != None and fps != None:
        base = os.path.splitext(video_path)[0]  # 拡張子を除いた部分を取得
        annotation_path = f"{base}.txt"  # 新しい拡張子を追加

        danger_path = os.path.join(output_path,"danger")
        safe_path = os.path.join(output_path,"safe")
        os.makedirs(danger_path,exist_ok=True)
        os.makedirs(safe_path,exist_ok=True)
        try:
            fps = int(fps)
        except ValueError:
            print("pfs must be int")
            return

        try:
            with open(annotation_path,'r') as f:
                annotation = json.load(f)
        except FileNotFoundError:
            print("annotation file does not found")
            return
        
        print(annotation)
        video = cv2.VideoCapture(video_path)
        original_fps = int(video.get(cv2.CAP_PROP_FPS))
        frame_count = video.get(cv2.CAP_PROP_FRAME_COUNT)
        step = int(original_fps/fps)

        current_frame = 0
        last_time = time.time()
        current_video_time = 0
        while True:
            
            if not isInValidArea(annotation,current_video_time):
                nearest_valid_area_start_time = getNeraresValidAreaStartTime(annotation,current_video_time)
                if nearest_valid_area_start_time == None:
                    print_progress_bar(frame_count,frame_count)
                    return
                else:
                    current_frame = int(nearest_valid_area_start_time*original_fps)
                    video.set(cv2.CAP_PROP_POS_FRAMES,current_frame)
            

            for _ in range(step):
                ret, frame = video.read()
                current_frame+=1
                if not ret:
                    print_progress_bar(frame_count,frame_count)
                    return
            current_video_time = current_frame/original_fps
            print(current_video_time)
            condition = getCondition(annotation,current_video_time)
            
            if condition == Condition.SAFE:
                saveImage(frame,safe_path,f"{int(current_frame)}.png")
            elif condition == Condition.DANGER:
                saveImage(frame,danger_path,f"{int(current_frame)}.png")
            

            current_time = time.time()
            if current_time-last_time > 0.1:
                last_time = current_time
                print_progress_bar(current_frame,frame_count)
    else:
        print(usage)

if __name__ == "__main__":
    usage = "usage: python ImageExtractor.py <video_path> <output_path> <fps>"
    
    args = sys.argv
    if len(args) < 4:
        print(usage)
        exit()
    video_path = args[1]
    output_path = args[2]
    fps = args[3]
    extractImage(video_path,output_path,fps)

