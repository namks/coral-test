# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A demo that runs object detection on camera frames using OpenCV.
TEST_DATA=../all_models
Run face detection model:
python3 detect.py \
  --model ${TEST_DATA}/mobilenet_ssd_v2_face_quant_postprocess_edgetpu.tflite
Run coco model:
python3 detect.py \
  --model ${TEST_DATA}/mobilenet_ssd_v2_coco_quant_postprocess_edgetpu.tflite \
  --labels ${TEST_DATA}/coco_labels.txt
"""
import argparse
import collections
import common
import cv2
import numpy as np
import os
from PIL import Image
import re
#import pyttsx3
import tflite_runtime.interpreter as tflite

Object = collections.namedtuple('Object', ['id', 'score', 'bbox'])

def load_labels(path):
    p = re.compile(r'\s*(\d+)(.+)')
    with open(path, 'r', encoding='utf-8') as f:
       lines = (p.match(line).groups() for line in f.readlines())
       return {int(num): text.strip() for num, text in lines}

class BBox(collections.namedtuple('BBox', ['xmin', 'ymin', 'xmax', 'ymax'])):
    """Bounding box.
    Represents a rectangle which sides are either vertical or horizontal, parallel
    to the x or y axis.
    """
    __slots__ = ()

def get_output(interpreter, score_threshold, top_k, image_scale=1.0):
    """Returns list of detected objects."""
    boxes = common.output_tensor(interpreter, 0)
    class_ids = common.output_tensor(interpreter, 1)
    scores = common.output_tensor(interpreter, 2)
    count = int(common.output_tensor(interpreter, 3))

    def make(i):
        ymin, xmin, ymax, xmax = boxes[i]
        return Object(
            id=int(class_ids[i]),
            score=scores[i],
            bbox=BBox(xmin=np.maximum(0.0, xmin),
                      ymin=np.maximum(0.0, ymin),
                      xmax=np.minimum(1.0, xmax),
                      ymax=np.minimum(1.0, ymax)))

    return [make(i) for i in range(top_k) if scores[i] >= score_threshold]

def main():
    default_model_dir = './all_models'
    #default_model = 'mobilenet_ssd_v2_face_quant_postprocess_edgetpu.tflite'
    default_model = 'mobilenet_ssd_v2_coco_quant_postprocess.tflite'
    default_labels = 'coco_labels.txt'  
    
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', help='.tflite model path',
                        default = default_model)
                        #default=os.path.join(default_model_dir,default_model))                        
    
    
    #################### Keondo's Modification #########################
    default_model2 = 'mask_detector_quant.tflite'
    #default_model2 = 'mask_detector_quant_edgetpu.tflite'
    parser.add_argument('--model2', help='.tflite model path',
                        default=default_model2)
    #################### Keondo's Modification #########################    
    
    parser.add_argument('--labels', help='label file path',
                        default = default_labels)
                        #default=os.path.join(default_model_dir, default_labels))

    parser.add_argument('--top_k', type=int, default=3,
                        help='number of categories with highest score to display')
    parser.add_argument('--camera_idx', type=int, help='Index of which video source to use. ', default = 0)
    parser.add_argument('--threshold', type=float, default=0.1,
                        help='classifier score threshold')
    args = parser.parse_args()
    
    #Initialize and configure pyttsx3 for warning messages    
    #engine = pyttsx3.init()
    #rate = engine.getProperty('rate')
    #engine.setProperty('rate', rate - 50)

    print('Loading {} with {} labels.'.format(args.model, args.labels))
    #interpreter = common.make_interpreter(args.model)
    interpreter = tflite.Interpreter(model_path = args.model)
    interpreter.allocate_tensors()
    
    #################### Keondo's Modification #########################
    #interpreter2 = common.make_interpreter(args.model2)
    interpreter2 = tflite.Interpreter(model_path = args.model2)
    interpreter2.allocate_tensors()
    print('Interpreter 2 loaded')
    #################### Keondo's Modification #########################  
    
    
    labels = load_labels(args.labels)

    cap = cv2.VideoCapture(args.camera_idx)

    frame_no = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        cv2_im = frame

        cv2_im_rgb = cv2.cvtColor(cv2_im, cv2.COLOR_BGR2RGB)
        pil_im = Image.fromarray(cv2_im_rgb)

        common.set_input(interpreter, pil_im)
        interpreter.invoke()
        objs = get_output(interpreter, score_threshold=args.threshold, top_k=args.top_k)
        #cv2_im = append_objs_to_img(cv2_im, objs, labels)
        
        #################### Keondo's Modification #########################
        #print('Interpreter 2 processing start')        
        #pil_im2 = pil_im.resize((224,224), resample=Image.NEAREST)
        #interpreter2.tensor(tensor_index)()[0][:,:] = pil_im2
        #pil_im2 = np.expand_dims(pil_im2, axis=0)
                
        height, width, channels = cv2_im.shape
        
        noMaskCount = 0
        
        mask_data = []
        
        i = 0
        
        #for obj in objs:
        for i in range(len(objs)-1,-1, -1):
            #x0, y0, x1, y1 = list(obj.bbox)
            x0, y0, x1, y1 = list(objs[i].bbox)
            x0, y0, x1, y1 = int(x0*width), int(y0*height), int(x1*width), int(y1*height)                        
            pil_im2 = Image.fromarray(cv2_im_rgb[y0:y1, x0:x1])
            print("Bf NN: ", frame_no, i, x0, y0)
            common.set_input2(interpreter2, pil_im2)
            output_data = common.output_tensor2(interpreter2)
            interpreter2.invoke()       
            print("Af NN: ", frame_no, i, x0, y0)
            print("Output data: ", output_data)
            mask_data.append((len(objs) - 1 - i, output_data))   
            #qi += 1
        
        j = 0
        
        #for obj in objs:
        for j in range(len(objs)):
            #x0, y0, x1, y1 = list(obj.bbox)
            x0, y0, x1, y1 = list(objs[j].bbox)
            x0, y0, x1, y1 = int(x0*width), int(y0*height), int(x1*width), int(y1*height)           
            
            print("2nd loop: ", frame_no, j, x0, y0)            
            print(list(filter(lambda x: x[0] == j, mask_data)))
            
            output = list(filter(lambda x: x[0] == j, mask_data))     
            
            mask, withoutMask = output[0][1]
                        
            if mask > withoutMask:
                labelMask = "Mask (" + str(x0) + "," + str(y0) + ")" 
                color = (255, 0, 0) #blue
            else:
                labelMask = "No Mask (" + str(x0) + "," + str(y0) + ")"   
                color = (0, 0, 255) #red
                noMaskCount += 1
            
            labelMask = "{}: {:.2f}%".format(labelMask, max(mask, withoutMask) * 100) 
            
            cv2_im = cv2.rectangle(cv2_im, (x0, y0), (x1, y1), color, 2)        
            cv2_im = cv2.putText(cv2_im, labelMask, (x0, y0-10),
                                 cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
            #j += 1
            
        frame_no += 1
        #if noMaskCount > 0:
        #    engine.say("There are " + str(noMaskCount) + "people not wearing masks. Please wear a mask")
            
        #tensor_index = interpreter2.get_input_details()[0]['index']
        #set_input2 = interpreter2.tensor(tensor_index)()
        #input_tensor2(interpreter2)[:,:] = pil_im2
        #interpreter2.tensor(tensor_index)()[0][:,:] = pil_im2
        #set_input2(pil_im2)
        #interpreter2.set_tensor(tensor_index, pil_im2)
        
        
        
        #output_details = interpreter2.get_output_details()[0]
        #output_data = np.squeeze(interpreter2.tensor(output_details['index'])())
        
        
        """
        There is at least 1 reference to internal data
      in the interpreter in the form of a numpy array or slice. Be sure to
      only hold the function returned from tensor() if you are using raw
      data access.
      """
        
        
        #print('Interpreter 2 Output data')
        #print(output_data)
        #if 'quantization' in output_details:
        #    print('quantization')
        #    print(output_details['quantization'])
        #elif 'quantization_parameters' in output_details:
        #    print('quantization_parameters')
        #    print(output_details['quantization_parameters'])
        #else:
        #    print('No quantization')
            
        #scales, zero_points, quantized_dimension = output_details['quantization_parameters']
        #if scales == 0:
        #    objs2 = output_data - zero_points
        #else:
        #    objs2 = scales * (output_data - zero_points)        
        
        #print('Check objs2')
        #print(objs2)
        

        #################### Keondo's Modification #########################    
        

        cv2.imshow('frame', cv2_im)
        #engine.runAndWait()
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def append_objs_to_img(cv2_im, objs, labels):
    height, width, channels = cv2_im.shape
    for obj in objs:
        x0, y0, x1, y1 = list(obj.bbox)
        x0, y0, x1, y1 = int(x0*width), int(y0*height), int(x1*width), int(y1*height)
        percent = int(100 * obj.score)
        label = '{}% {}'.format(percent, labels.get(obj.id, obj.id))

        cv2_im = cv2.rectangle(cv2_im, (x0, y0), (x1, y1), (0, 255, 0), 2)
        cv2_im = cv2.putText(cv2_im, label, (x0, y0+30),
                             cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2)
    return cv2_im

if __name__ == '__main__':
    main()
