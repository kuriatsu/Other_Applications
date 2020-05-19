#! /usr/bin/python3
# -*- coding: utf-8 -*-
"""
welcome to PIE data visualize

"""

import cv2
import argparse
import numpy as np
import time
import datetime
import csv
import xml.etree.ElementTree as ET


class PieDataVisualize(object):

    def __init__(self, args):
        # static object
        self.pie_data = {}
        self.attrib_tree = None

        self.icon_dict = {
            'walker_cross_to_left':
                {
                'path':args.icon_path + 'walker_cross_to_left.png'
                },
            'walker_cross_to_right':
                {
                'path':args.icon_path + 'walker_cross_to_right.png'
                },
            'tf_red':
                {
                'path':args.icon_path + 'tf_red.png'
                },
            'tf_green':
                {
                'path':args.icon_path + 'tf_green.png'
                }
            }

        # static variables calcurated in this class
        self.image_res = args.res
        self.modified_video_rate = None
        self.image_crop_rate = args.image_crop_rate
        self.window_name = 'frame'
        self.obj_spawn_frame_min = None
        self.obj_spawn_frame_max = None

        # log
        self.log_file = args.log
        self.log = []

        # dynamic object
        self.video = None
        self.current_frame_num = None
        self.target_obj_dict = [[0]]


    def __enter__(self):
        return self


    def prepareIcon(self):

        for icon_info in self.icon_dict.values():
            img = cv2.imread(icon_info.get('path'))
            icon_info['roi'] = img.shape[:2]
            img2grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            ret, mask = cv2.threshold(img2grey, 10, 255, cv2.THRESH_BINARY)
            # ret, mask = cv2.threshold(img2grey, 200, 255, cv2.THRESH_BINARY_INV)
            icon_info['mask_inv'] = cv2.bitwise_not(mask)
            icon_info['icon_fg'] = cv2.bitwise_and(img, img, mask=mask)


    def getVideo(self, args):

        try:
            self.video = cv2.VideoCapture(args.video)

        except:
            print('cannot open video')
            exit(0)

        # get video rate and change variable unit from time to frame num
        video_rate = int(self.video.get(cv2.CAP_PROP_FPS))
        self.obj_spawn_frame_max = args.obj_spawn_time_max * video_rate
        self.obj_spawn_frame_min = args.obj_spawn_time_min * video_rate
        print(video_rate)

        # adjust video rate to keep genuine broadcast rate
        self.modified_video_rate = video_rate + args.rate_offset

        # calc image crop region crop -> expaned to original frame geometry
        offset_yt = self.image_res[0] * ((1.0 - self.image_crop_rate) * 0.5 + args.image_crop_offset_y)
        offset_xl = self.image_res[1] * (1.0 - self.image_crop_rate) * 0.5
        self.image_offset = [int(offset_yt),
                             int(offset_yt + self.image_res[0] * self.image_crop_rate),
                             int(offset_xl),
                             int(offset_xl + self.image_res[1] * self.image_crop_rate)
                             ]


    def getAttrib(self, attrib_file):
        try:
            tree = ET.parse(attrib_file)
            self.attrib_tree = tree.getroot()
            del tree
        except:
            print('cannot open attrib file')
            exit(0)


    def getAnno(self, anno_file):
        try:
            tree = ET.parse(anno_file)
            root = tree.getroot()
        except:
            print('cannot open annotation file')
            exit(0)

        for track in root.findall('track'):

            for anno_itr in track.iter('box'):

                anno_info = {}

                # get id
                for attribute in anno_itr.findall('attribute'):
                    if attribute.attrib.get('name') == 'id':
                        anno_id = attribute.text

                # get basic information
                anno_info['label'] = track.attrib.get('label')
                anno_info['xbr'] = int((float(anno_itr.attrib.get('xbr')) - self.image_offset[2]) * (1 / self.image_crop_rate))
                anno_info['xtl'] = int((float(anno_itr.attrib.get('xtl')) - self.image_offset[2]) * (1 / self.image_crop_rate))
                anno_info['ybr'] = int((float(anno_itr.attrib.get('ybr')) - self.image_offset[0]) * (1 / self.image_crop_rate))
                anno_info['ytl'] = int((float(anno_itr.attrib.get('ytl')) - self.image_offset[0]) * (1 / self.image_crop_rate))
                # print(anno_info)

                # if object is pedestrian, get additional information
                if anno_info['label'] == 'pedestrian':
                    for attrib_itr in self.attrib_tree.iter('pedestrian'):
                        if attrib_itr.attrib.get('id') == anno_id:
                            anno_info['intention_prob'] = attrib_itr.attrib.get('intention_prob')
                            anno_info['critical_point'] = attrib_itr.attrib.get('critical_point')
                            anno_info['crossing_point'] = attrib_itr.attrib.get('crossing_point')
                            anno_info['exp_start_point'] = attrib_itr.attrib.get('exp_start_point')

                            # if the pedestrian framed out, save the frame num and apply it to the already added data in self.pie_data[]
                            if 'frameout_point' in attrib_itr.attrib:
                                anno_info['frameout_point'] = attrib_itr.attrib.get('frameout_point')

                            else:
                                # if the pedestrian framed out now, save framenum and apply it to all obj with same id
                                if(anno_info['xbr'] > self.image_res[1] or anno_info['xtl'] < 0):
                                    anno_info['frameout_point'] = anno_itr.attrib.get('frame')
                                    attrib_itr.attrib['frameout_point'] = anno_itr.attrib.get('frame')

                                    # scan the already added object in self.pie_data[]
                                    for frame_obj in self.pie_data.values():
                                        for obj_id, obj_info in frame_obj.items():
                                            if obj_id == anno_id:
                                                obj_info['frameout_point'] = anno_itr.attrib.get('frame')

                # add to pie_data dictionary
                if anno_itr.attrib.get('frame') not in self.pie_data:
                    self.pie_data[anno_itr.attrib.get('frame')] = {}

                self.pie_data[anno_itr.attrib.get('frame')][anno_id] = anno_info

        # delete objects to improve performance
        del root
        del tree
        del self.attrib_tree


    def prepareEventHandler(self):
        """add mouse click callback to the window
        """
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.touchCallback)


    def touchCallback(self, event, x, y, flags, param):
        """if mouce clicked, check position and judge weather the position is on the rectange or not
        """
        # if the event handler is leftButtonDown and current frame contains objects
        if event == cv2.EVENT_LBUTTONDOWN and self.current_frame_num in self.pie_data:

            for obj_id, obj_info in self.pie_data[self.current_frame_num].items():

                # if the clicked position is on the rectangle of one of the objects
                if int(float(obj_info['xtl'])) < x < int(float(obj_info['xbr'])) and int(float(obj_info['ytl'])) < y < int(float(obj_info['ybr'])):

                    # if the clicked position is on the focuced object
                    if self.target_obj_dict[obj_id]['is_forcused']:

                        # update "is_forcused" in self.dislpayed_obj
                        self.updateFocusedObject(obj_id)
                        self.log[-1].append([self.current_frame_num, time.time()])
                        return


    def pushCallback(self):
        """callback of enter key push, target is focused object
        """
        for obj_id, obj_info in self.target_obj_dict.items():
            if obj_info['is_forcused']:
                self.updateFocusedObject(obj_id)
                self.log[-1].append([self.current_frame_num, time.time()])
                return


    def refleshTargetObjDict(self):
        """magage displaying object
        is_checked ; flag wether the subject check obj and input some action or not
        """
        new_target_obj = {} # new container
        is_forcused_obj_exist = False # flag

        for obj_id, obj_info in self.pie_data[self.current_frame_num].items():

            if obj_info['label'] != 'pedestrian': continue

            # if the obj was already displayed
            if obj_id in self.target_obj_dict:

                new_target_obj[obj_id] = self.target_obj_dict[obj_id]
                new_target_obj[obj_id]['is_spawn_range'] = self.obj_spawn_frame_min < (int(obj_info['frameout_point']) - int(self.current_frame_num)) < self.obj_spawn_frame_max
                # if the object was forcused
                if self.target_obj_dict[obj_id]['is_forcused']:
                    is_forcused_obj_exist = True

            # if the obj is new
            else:
                new_target_obj[obj_id] = {'is_forcused':False,
                                          'is_checked':False,
                                          'is_spawn_range':self.obj_spawn_frame_min < (int(obj_info['frameout_point']) - int(self.current_frame_num)) < self.obj_spawn_frame_max}
                # print('{} < {}'.format(int(obj_info['frameout_point'])- int(self.current_frame_num), self.display_time))

        # reflesh displaying object container
        self.target_obj_dict = new_target_obj

        # if the forcused object is not checked, don't search new forcused obj
        if not is_forcused_obj_exist:
            self.updateFocusedObject()


    def updateFocusedObject(self, checked_obj_id=None):
        """find focused object from self.target_obj_dict
        """
        min_obj_id = None # initial variable for searching new imporant objects
        min_time = 20000 # initial variable for searching new imporant objects

        # is this method called by callback, checked_obj_id has target object id which is checked and should be unfocused
        if checked_obj_id is not None:
            self.target_obj_dict[checked_obj_id]['is_checked'] = True
            self.target_obj_dict[checked_obj_id]['is_forcused'] = False

        # find new focused object
        for obj_id, obj_info in self.target_obj_dict.items():
            # search the new forcused obj
            if not obj_info['is_checked'] and obj_info['is_spawn_range']:
            # if not obj_info['is_checked'] and obj_info['is_spawn_range'] and int(self.pie_data[self.current_frame_num][obj_id]['frameout_point']) < min_time:
                # print(obj_info['is_spawn_range'])
                min_obj_id = obj_id
                min_time = int(self.pie_data[self.current_frame_num][obj_id]['frameout_point'])

        # if the new forcused obj is found, add the flag
        if min_obj_id is not None:
            self.target_obj_dict[min_obj_id]['is_forcused'] = True


    def renderInfo(self, image):
        """add information to the image

        """
        # loop for each object in the frame from PIE dataset
        for obj_id, displayed_obj_info in self.target_obj_dict.items():

            obj_info = self.pie_data[self.current_frame_num][obj_id]

            if displayed_obj_info['is_forcused']: # if forcused --- red
                color = (0, 0, 255)
                # if self.current_frame_num == obj_info['frameout_point']:
                #     print('frame_out')
                #     color = (255, 0, 255)
                #     print(obj_info)
                self.drawIcon(image, obj_info)

                # cv2.putText(
                #     image,
                #     'Cross?',
                #     (int(float(obj_info['xtl'])), int(float(obj_info['ytl'])) - 10),
                #     cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA
                #     )

                # print((float(obj_info['frameout_point']) - float(self.current_frame_num)) * 5 / self.display_time)
                # print(displayed_obj_info['is_spawn_range'])
                cv2.putText(
                    image,
                    '{:.01f}%'.format(float(obj_info['intention_prob']) * 100),
                    (int(float(obj_info['xtl'])), int(float(obj_info['ytl'])) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA
                    )

                image = cv2.rectangle(image,
                (int(float(obj_info['xtl'])), int(float(obj_info['ytl']))),
                (int(float(obj_info['xbr'])), int(float(obj_info['ybr']))),
                color,
                1)

                # try:
                #     scale = 50.0 / (float(obj_info['xbr']) - float(obj_info['xtl']))
                #     pedestrian_image = cv2.resize(image[int(float(obj_info['ytl'])):int(float(obj_info['ybr'])), int(float(obj_info['xtl'])):int(float(obj_info['xbr']))], dsize=None, fx=scale, fy=scale)
                #     print('pedestrian rendered, y:', pedestrian_image.shape[0], pedestrian_image.shape[1])
                #     # image[500:500+pedestrian_image.shape[0], 500:500+pedestrian_image.shape[1]] = pedestrian_image
                #     image[int(float(obj_info['ytl'])) - pedestrian_image.shape[0]:int(float(obj_info['ytl'])), int(float(obj_info['xbr']) - pedestrian_image.shape[1]*0.5):int(float(obj_info['xbr']) + pedestrian_image.shape[1]*0.5)] = pedestrian_image
                #
                # except:
                #     print('pedestrian render is out of image')

                self.log.append([self.current_frame_num,
                                 time.time(),
                                 obj_id,
                                 obj_info['intention_prob'],
                                 obj_info['critical_point'],
                                 obj_info['crossing_point'],
                                 obj_info['exp_start_point'],
                                 ])

            elif displayed_obj_info['is_checked']: # if checked --- green
                color = (0, 255, 0)

            elif displayed_obj_info['is_spawn_range']: # passed --- blue
                color = (255, 0, 0)

            else:
                color = (0,0,0)


            # image = cv2.rectangle(image,
            # (int(float(obj_info['xtl'])), int(float(obj_info['ytl']))),
            # (int(float(obj_info['xbr'])), int(float(obj_info['ybr']))),
            # color,
            # 1)

    def drawIcon(self, image, obj_info):
        """draw icon to emphasize the target objects
        image : image
        obj_info : PIE dataset info of the object in the frame
        """

        icon_offset_y = 30.0
        icon_offset_x = int((self.icon_roi[1] - (float(obj_info['xbr']) - float(obj_info['xtl']))) * 0.5)

        # position of the icon
        icon_ytl = int(float(obj_info['ytl']) - self.icon_roi[0] - icon_offset_y)
        icon_xtl = int(float(obj_info['xtl']) - icon_offset_x)
        icon_ybr = int(float(obj_info['ytl']) - icon_offset_y)
        icon_xbr = int(float(obj_info['xtl']) + self.icon_roi[1] - icon_offset_x)

        # put icon on image
        try:
            roi = image[icon_ytl:icon_ybr, icon_xtl:icon_xbr] # get roi from image
            image_bg = cv2.bitwise_and(roi, roi, mask=self.mask_inv) # remove color from area for icon by filter
            buf = cv2.add(self.icon_fg, image_bg) # put icon of roi
            image[icon_ytl:icon_ybr, icon_xtl:icon_xbr] = buf # replace image region to roi

        except:
            print('icon is out of range y:{}-{}, x:{}-{}'.format(icon_ytl, icon_ybr, icon_xtl, icon_xbr))


    def loop(self):

        print('start_loop')

        sleep_time = self.modified_video_rate
        frame = 0

        while(self.video.isOpened()):

            start = time.time()
            self.current_frame_num = str(frame)
            ret, image = self.video.read()


            # preprocess image . crop + resize
            scale = 1.0 / self.image_crop_rate
            image = cv2.resize(image[self.image_offset[0]:self.image_offset[1], self.image_offset[2]:self.image_offset[3]], dsize=None, fx=scale, fy=scale)

            if self.current_frame_num in self.pie_data:
                self.refleshTargetObjDict() # udpate self.target_obj_dict
                self.renderInfo(image) # add info to the image

            cv2.imshow(self.window_name, image) # render

            #  calc sleep time to keep frame rate to be same with video rate
            sleep_time = max(int((1000 / (self.modified_video_rate) - (time.time() - start))), 1)

            # sleep and wait quit key
            key = cv2.waitKey(sleep_time) & 0xFF
            if key is not 255 : print(key)
            if key == ord('q'):
                break
            if key == 13:
                self.pushCallback()

            frame += 1

        exit(1)


    def __exit__(self, exc_type, exc_value, traceback):
        print('delete instance... type: {}, value: {}, traceback: {}'.format(exc_type, exc_value, traceback))

        self.video.release()
        cv2.destroyAllWindows()

        with open(self.log_file, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['display_frame', 'display_time', 'id', 'intention_prob', 'critical_point', 'crossing_point', 'exp_start_point'])
            writer.writerows(self.log)


def main():
    parser_res = lambda x : list(map(float, x.split('x')))

    argparser = argparse.ArgumentParser( description = __doc__)
    argparser.add_argument(
        '--video', '-v',
        metavar='VIDEO',
        default='/media/ssd/PIE_data/PIE_clips/set01/video_0001.mp4')
    argparser.add_argument(
        '--anno',
        metavar='ANNO',
        default='/media/ssd/PIE_data/annotations/set01/video_0001_annt.xml')
    argparser.add_argument(
        '--attrib',
        metavar='ATTRIB',
        default='/media/ssd/PIE_data/annotations_attributes/set01/video_0001_attributes.xml')
    argparser.add_argument(
        '--rate_offset',
        metavar='OFFSET',
        default=15)
    argparser.add_argument(
        '--log',
        metavar='LOG',
        default='/home/kuriatsu/share/{}_intervene_time.csv'.format(datetime.date.today()))
    argparser.add_argument(
        '--image_crop_rate',
        metavar='SCALE',
        default=0.6)
    argparser.add_argument(
        '--image_crop_offset_y',
        metavar='OFFSET',
        default=0.2)
    argparser.add_argument(
        '--res',
        metavar='height x width',
        type=parser_res,
        default='1080x1900')
    argparser.add_argument(
        '--obj_spawn_time_min',
        metavar='MIN_TIME',
        default=2)
    argparser.add_argument(
        '--obj_spawn_time_max',
        metavar='MAX_TIME',
        default=46)
    argparser.add_argument(
        '--icon_path',
        metavar='/path/to/icon/files',
        default='/home/kuriatsu/share/')
    args = argparser.parse_args()

    with PieDataVisualize(args) as pie_data_visualize:
        pie_data_visualize.getVideo(args)
        pie_data_visualize.getAttrib(args.attrib)
        pie_data_visualize.getAnno(args.anno)
        pie_data_visualize.prepareIcon()
        pie_data_visualize.prepareEventHandler()
        pie_data_visualize.loop()

if __name__ == '__main__':
    main()
