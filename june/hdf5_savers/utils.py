import numpy as np
import re


def read_dataset(dataset, index1=None, index2=None):
    if index1 is None:
        index1 = 0
    if index2 is None:
        index2 = dataset.len()
    dataset_shape = dataset.shape
    if len(dataset_shape) > 1:
        load_shape = [index2-index1] + list(dataset_shape[1:])
    else:
        load_shape = index2-index1
    ret = np.empty(load_shape, dtype=dataset.dtype)
    dataset.read_direct(ret, np.s_[index1:index2], np.s_[0:index2-index1])
    return ret

def write_dataset(group, dataset_name, data, index1 = None, index2 = None):
    if dataset_name not in group:
        if len(data.shape) > 1:
            maxshape=(None, *data.shape[1:])
        else:
            maxshape = (None,)
        group.create_dataset(dataset_name, data=data, maxshape=maxshape)
    else:
        if len(data.shape) > 1:
            newshape = (group[dataset_name].shape[0] + data.shape[0], *data.shape[1:])
        else:
            newshape = (group[dataset_name].shape[0] + data.shape[0],)
        group[dataset_name].resize(newshape)
        group[dataset_name][index1:index2] = data


def __multi_replace_re(replacements):
    return re.compile("({})".format("|".join(map(re.escape, replacements.keys()))))


def multi_replace(replacements, value, regex=None):
    regex = regex or __multi_replace_re(replacements)
    return regex.sub(lambda m: replacements[m.string[m.start():m.end()]], value)


__escape_umlaute_replacements = {"ä": '"ae', "ö": '"oe', "ü": '"ue', "ß": '"ss'}
__escape_umlaute_re = __multi_replace_re(__escape_umlaute_replacements)
def escape_umlaute(x):
    return multi_replace(
        replacements=__escape_umlaute_replacements,
        value=x,
        regex=__escape_umlaute_re,
    )


__unescape_umlaute_replacements = {'"ae': "ä", '"oe': "ö", '"ue': "ü", '"ss': "ß"}
__unescape_umlaute_re = __multi_replace_re(__unescape_umlaute_replacements)
def unescape_umlaute(x):
    return multi_replace(
        replacements=__unescape_umlaute_replacements,
        value=x,
        regex=__unescape_umlaute_re,
    )
