"""
Test zero-shot YOLO detection model on unseen classes.
"""

import os

import numpy as np
from PIL import Image
from keras import backend as K
from keras.layers import Input
from tqdm import tqdm

from yolo3.model import yolo_body, yolo_eval
from yolo3.utils import letterbox_image

with open('model_data/1505split_names.txt') as f:
    class_names = f.readlines()
class_names = [c.strip() for c in class_names]


class YOLO(object):
    def __init__(self):
        self.weight_path = 'logs/voc/trained_weights.h5'
        self.anchors_path = 'model_data/yolo_anchors.txt'
        self.attribute_path = 'model_data/1505attributes.npy'
        self.predict_dir = 'data/predicted/'
        self.score = 0.001
        self.iou = 0.5
        self.num_seen = 15
        self.anchors = self._get_anchors()
        self.sess = K.get_session()
        self.model_image_size = (416, 416)  # fixed size or (None, None), hw
        self.boxes, self.scores, self.classes = self.generate()

    def _get_anchors(self):
        anchors_path = os.path.expanduser(self.anchors_path)
        with open(anchors_path) as f:
            anchors = f.readline()
        anchors = [float(x) for x in anchors.split(',')]
        return np.array(anchors).reshape(-1, 2)

    def generate(self):
        model_path = os.path.expanduser(self.weight_path)
        assert model_path.endswith('.h5'), 'Keras model or weights must be a .h5 file.'

        # Load model, or construct model and load weights.
        num_anchors = len(self.anchors)

        self.yolo_model = yolo_body(Input(shape=(None, None, 3)), self.num_seen, num_anchors // 3)
        self.yolo_model.load_weights(self.weight_path, by_name=True)
        print('{} model, anchors and classes loaded.'.format(model_path))

        # Generate output tensor targets for filtered bounding boxes.
        attribute = np.load(self.attribute_path)
        self.input_image_shape = K.placeholder(shape=(2,))
        boxes, scores, classes = yolo_eval(self.yolo_model.output, self.anchors, self.num_seen,
                                           attribute, self.input_image_shape,
                                           score_threshold=self.score, iou_threshold=self.iou)
        return boxes, scores, classes

    def detect_image(self, image_path):
        image = Image.open(image_path)

        if self.model_image_size != (None, None):
            assert self.model_image_size[0] % 32 == 0, 'Multiples of 32 required'
            assert self.model_image_size[1] % 32 == 0, 'Multiples of 32 required'
            boxed_image = letterbox_image(image, tuple(reversed(self.model_image_size)))
        else:
            new_image_size = (image.width - (image.width % 32),
                              image.height - (image.height % 32))
            boxed_image = letterbox_image(image, new_image_size)
        image_data = np.array(boxed_image, dtype='float32')

        image_data /= 255.
        image_data = np.expand_dims(image_data, 0)  # Add batch dimension.

        out_boxes, out_scores, out_classes = self.sess.run(
            [self.boxes, self.scores, self.classes],
            feed_dict={
                self.yolo_model.input: image_data,
                self.input_image_shape: [image.size[1], image.size[0]],
                K.learning_phase(): 0
            })

        image_name = image_path.split('/')[-1].split('.')[0]
        with open(os.path.join(self.predict_dir, image_name + '.txt'), 'w') as f:
            for i, c in enumerate(out_classes):
                class_name = class_names[self.num_seen:][c]
                confidence = out_scores[i]
                box = out_boxes[i]

                top, left, bottom, right = box
                top = max(0, np.floor(top + 0.5).astype('int32'))
                left = max(0, np.floor(left + 0.5).astype('int32'))
                bottom = min(image.size[1], np.floor(bottom + 0.5).astype('int32'))
                right = min(image.size[0], np.floor(right + 0.5).astype('int32'))
                f.write('{} {} {} {} {} {}\n'.format(class_name, confidence, left, top, right, bottom))

    def close_session(self):
        self.sess.close()


def _main():
    test_path = 'data/test.txt'

    yolo = YOLO()
    with open(test_path) as rf:
        test_img = rf.readlines()
    test_img = [c.strip() for c in test_img]

    for img in tqdm(test_img):
        img_path = img.split()[0]
        yolo.detect_image(img_path)
    K.clear_session()


if __name__ == '__main__':
    # os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    # os.environ['CUDA_VISIBLE_DEVICES'] = '1,2,3'
    with K.tf.device('/gpu:1'):
        config = K.tf.ConfigProto()
        # config.gpu_options.allow_growth = True
        config.gpu_options.per_process_gpu_memory_fraction = 0.8
        session = K.tf.Session(config=config)
        K.set_session(session)
    _main()
