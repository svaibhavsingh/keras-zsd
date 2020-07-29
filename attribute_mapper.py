import numpy as np
def map_attributes():
    attribute_path = 'model_data/attributes.npy'
    new_classes_order = 'model_data/voc_classes.txt'
    file_to_save = 'model_data/1505attributes.npy'
    with open('model_data/1505split_names.txt') as f:
        classes = f.readlines()
    classes = [c.strip() for c in classes]
    mappings = []
    with open(new_classes_order) as f:
        new_classes = f.readlines()
    new_classes = [c.strip() for c in new_classes]
    for i in range(len(new_classes)):
        mappings.append(classes.index(new_classes[i]))
    attribute = np.load(attribute_path)[mappings, :]
    np.save(file_to_save, attribute)
    return
map_attributes()