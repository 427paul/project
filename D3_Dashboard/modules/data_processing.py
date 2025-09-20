import numpy as np
def calculate_percentage(val, total):
    percent = np.round((np.divide(val, total) * 100), 2)
    return percent
def data_creation(data, percent, class_labels, group=None):
     for index, item in enumerate(percent):
        data_instance = {}
        data_instance['category'] = class_labels[index]
        data_instance['value'] = item
        data_instance['group'] = group
        data.append(data_instance)