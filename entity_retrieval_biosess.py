# coding=utf-8
# Copyright 2018 The Google AI Language Team Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# BERT finetuning runner.
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import csv
import os,sys
from turtle import pos

import modeling_modif
# import optimization
import optimization_layer_lr as optimization
import tokenization
# import tensorflow.compat.v1 as tf
import tensorflow as tf
import scipy
import numpy as np
import random
import ABCNN
from tensorflow.contrib.layers.python.layers import initializers
import joblib
from get_similarity import external_similarity, get_sim

flags = tf.flags

FLAGS = flags.FLAGS

## Required parameters
flags.DEFINE_string(
    "data_dir", 'glue_data/textsim',
    "The input data dir. Should contain the .tsv files (or other data files) "
    "for the task.")

flags.DEFINE_string(
    "retrieve_dir", 'glue_data/textsim',
    "The input data dir. Should contain the .tsv files (or other data files) "
    "for the task.")

flags.DEFINE_string(
    "bert_config_file", 'uncased_L-12_H-768_A-12/bert_config.json',
    "The config json file corresponding to the pre-trained BERT model. "
    "This specifies the model architecture.")

flags.DEFINE_string("task_name", 'Textsim', "The name of the task to train.")

flags.DEFINE_string("vocab_file", 'uncased_L-12_H-768_A-12/vocab.txt',
                    "The vocabulary file that the BERT model was trained on.")

flags.DEFINE_string(
    "output_dir", './tmp/textsim_output_gate_1220_1/',
    "The output directory where the model checkpoints will be written.")

## Other parameters

flags.DEFINE_string(
    "init_checkpoint", './tmp/pretraining_output/model.ckpt-200000',
    "Initial checkpoint (usually from a pre-trained BERT model).")

flags.DEFINE_bool(
    "do_lower_case", True,
    "Whether to lower case the input text. Should be True for uncased "
    "models and False for cased models.")

flags.DEFINE_integer(
    "max_seq_length", 384,
    "The maximum total input sequence length after WordPiece tokenization. "
    "Sequences longer than this will be truncated, and sequences shorter "
    "than this will be padded.")

flags.DEFINE_integer(
    "entity_vec", 100,
    "vector length of entity vector.")

flags.DEFINE_bool("do_train_and_eval", True, "Whether to run training and eval.")

flags.DEFINE_bool("do_train", False, "Whether to run training.")

flags.DEFINE_bool("do_eval", False, "Whether to run eval on the dev set.")

flags.DEFINE_bool(
    "do_predict", True,
    "Whether to run the model in inference mode on the test set.")

flags.DEFINE_integer("train_batch_size", 10, "Total batch size for training.")

flags.DEFINE_integer("eval_batch_size", 8, "Total batch size for eval.")

flags.DEFINE_integer("predict_batch_size", 8, "Total batch size for predict.")

flags.DEFINE_float("learning_rate", 3e-5, "The initial learning rate for Adam.")

flags.DEFINE_float("other_learning_rate", 1e-5, "The other params learning rate for Adam.")

flags.DEFINE_integer('lstm_size',300, 'size of lstm units')

flags.DEFINE_integer('num_layers', 1, 'number of rnn layers, default is 1')

flags.DEFINE_float("num_train_epochs", 10.0,
                   "Total number of training epochs to perform.")

flags.DEFINE_float("max_train_epochs", 10, "Total number of training epochs to perform.")

flags.DEFINE_float(
    "warmup_proportion", 0.1,
    "Proportion of training to perform linear learning rate warmup for. "
    "E.g., 0.1 = 10% of training.")

flags.DEFINE_integer("save_checkpoints_steps", 1000,
                     "How often to save the model checkpoint.")

flags.DEFINE_integer("iterations_per_loop", 1000,
                     "How many steps to make in each estimator call.")

flags.DEFINE_bool("use_tpu", False, "Whether to use TPU or GPU/CPU.")

tf.flags.DEFINE_string(
    "tpu_name", None,
    "The Cloud TPU to use for training. This should be either the name "
    "used when creating the Cloud TPU, or a grpc://ip.address.of.tpu:8470 "
    "url.")

tf.flags.DEFINE_string(
    "tpu_zone", None,
    "[Optional] GCE zone where the Cloud TPU is located in. If not "
    "specified, we will attempt to automatically detect the GCE project from "
    "metadata.")

tf.flags.DEFINE_string(
    "gcp_project", None,
    "[Optional] Project name for the Cloud TPU-enabled project. If not "
    "specified, we will attempt to automatically detect the GCE project from "
    "metadata.")

tf.flags.DEFINE_string("master", None, "[Optional] TensorFlow master URL.")

flags.DEFINE_integer(
    "num_tpu_cores", 8,
    "Only used if `use_tpu` is True. Total number of TPU cores to use.")

flags.DEFINE_integer(
    "max_word_length", 10,
    "maximum length of a word."
)

flags.DEFINE_integer(
    "char_embed_dim", 30,
    "char embedding dimension."
)

flags.DEFINE_integer(
    "char_vocab_size", 70,
    "the size of char vocabulary."
)


flags.DEFINE_integer(
    "abcnn_max_seqlen",380,
    "the size of char vocabulary."
)

flags.DEFINE_integer(
    "random_seed", 10,
    "the size of char vocabulary."
)

# char dict 
flags.DEFINE_string("char_vocab_file", './char_vocab.txt',
                    "The char vocabulary file that the BERT model was trained on.")

np.random.seed(FLAGS.random_seed)
tf.set_random_seed(FLAGS.random_seed)
random.seed(FLAGS.random_seed)

class InputExample(object):
  """A single training/test example for simple sequence classification."""

  def __init__(self, guid, text_a, text_b=None, label=None, hand_fea=None,entity_a=None,entity_b=None,entity_a_kb=None,entity_b_kb=None, retriv_a=None, retriv_b=None):
    """Constructs a InputExample.

    Args:
      guid: Unique id for the example.
      text_a: string. The untokenized text of the first sequence. For single
        sequence tasks, only this sequence must be specified.
      text_b: (Optional) string. The untokenized text of the second sequence.
        Only must be specified for sequence pair tasks.
      label: (Optional) string. The label of the example. This should be
        specified for train and dev examples, but not for test examples.
    """
    self.guid = guid
    self.text_a = text_a
    self.text_b = text_b
    self.label = label
    self.hand_fea = hand_fea
    self.entity_a = entity_a
    self.entity_b = entity_b
    self.entity_a_kb = entity_a_kb
    self.entity_b_kb = entity_b_kb
    self.retriv_a = retriv_a
    self.retriv_b = retriv_b


class InputFeatures(object):
  """A single set of features of data."""

  def __init__(self, input_ids, input_mask, segment_ids, entity_ids, label_value,hand_fea,char_ids,entity_a,entity_b,entity_a_kb,entity_b_kb,similarity, retriv_tokens_ids, retrieve_segment_ids,retrieve_mask):
    self.input_ids = input_ids
    self.input_mask = input_mask
    self.segment_ids = segment_ids
    self.entity_ids = entity_ids
    self.label_value = label_value
    self.hand_fea = hand_fea
    self.char_ids = char_ids
    self.entity_a = entity_a
    self.entity_b = entity_b
    self.entity_a_kb = entity_a_kb
    self.entity_b_kb = entity_b_kb
    self.similarity = similarity
    self.retriv_tokens_ids = retriv_tokens_ids
    self.retrieve_segment_ids = retrieve_segment_ids
    self.retrieve_mask = retrieve_mask

class DataProcessor(object):
  """Base class for data converters for sequence classification data sets."""

  def get_train_examples(self, data_dir):
    """Gets a collection of `InputExample`s for the train set."""
    raise NotImplementedError()

  def get_dev_examples(self, data_dir):
    """Gets a collection of `InputExample`s for the dev set."""
    raise NotImplementedError()

  def get_test_examples(self, data_dir):
    """Gets a collection of `InputExample`s for prediction."""
    raise NotImplementedError()

  def get_labels(self):
    """Gets the list of labels for this data set."""
    raise NotImplementedError()

  @classmethod
  def _read_tsv(cls, input_file, quotechar=None):
    """Reads a tab separated value file."""
    with tf.gfile.Open(input_file, "r") as f:
      reader = csv.reader(f, delimiter="\t", quotechar=quotechar)
      lines = []
      for line in reader:
        lines.append(line)
      return lines
  
  def _read_sts_data(cls, data_file):
    with tf.gfile.Open(data_file, "r") as f:
      lines = f.readlines()
      contents = []
      for i, line in enumerate(lines):
        content = line.strip().split('\t')
        contents.append({"id":i, "s1":content[0], "s2":content[1], "pos1":content[2], "pos2":content[3], "entity1":content[4], "entity2":content[5], "score":content[-1]})
      return contents
  
  def _read_retriev_data(cls, retrieve_file):
    with tf.gfile.Open(retrieve_file, "r") as f:
      lines = f.readlines()
      retrives = []
      for i in range(int(len(lines)/2)):
        sen1_retriv = lines[i*2].split('\t')[0]
        sen2_retriv = lines[i*2+1].split('\t')[0]
        retrives.append((sen1_retriv, sen2_retriv))
      return retrives

class TextsimProcessor(DataProcessor):
  """Processor for the MRPC data set (GLUE version)."""
  def get_train_examples(self, data_dir, retrieve_dir):
    """See base class."""
    lines = self._read_sts_data(os.path.join(data_dir, "all_kg.txt"))
    retrives = self._read_retriev_data(os.path.join(retrieve_dir, "all_neighbor.txt"))
    return self._create_examples(lines, retrives, "train")
 
  def get_dev_examples(self, data_dir, retrieve_dir):
    """See base class."""
    lines = self._read_sts_data(os.path.join(data_dir, "all_kg.txt"))
    retrives = self._read_retriev_data(os.path.join(retrieve_dir, "all_neighbor.txt"))
    return self._create_examples(lines, retrives, "dev")

  def get_test_examples(self, data_dir, retrieve_dir):
    """See base class."""
    # lines = self._read_sts_data("/disk2/xy_disk2/thesis/STS/LAP/data/2019n2c2/test_data/test_kg.txt")
    lines = self._read_sts_data(os.path.join(data_dir, "all_kg.txt"))
    retrives = self._read_retriev_data(os.path.join(retrieve_dir, "all_neighbor.txt"))
    return self._create_examples(lines, retrives, "test")
 

  def get_labels(self):
    """See base class."""
    return ["0", "1"]

  def _create_examples(self, lines, retrives, set_type):
    """Creates examples for the training and dev sets."""
    examples = []
    for idx in range(len(lines)):
      
      guid = "%s-%s" % (set_type, tokenization.convert_to_unicode(str(idx)))
      text_a = tokenization.convert_to_unicode(lines[idx]['s1'])
      text_b = tokenization.convert_to_unicode(lines[idx]['s2'])
      label = tokenization.convert_to_unicode(lines[idx]['score'])
      abcnn_input_a = lines[idx]['entity1']
      abcnn_input_b = lines[idx]['entity2']

      retriv_a, retriv_b = retrives[idx]

      if set_type == "test":
        label = "0"
      
      examples.append(
          InputExample(guid=guid, text_a=text_a, text_b=text_b, label=label, hand_fea=None,\
                        entity_a=abcnn_input_a, entity_b=abcnn_input_b, \
                        entity_a_kb=None, entity_b_kb=None, retriv_a=retriv_a, retriv_b=retriv_b))
    return examples


def convert_single_example(ex_index, example, label_list, max_seq_length,
                           tokenizer, char_tokenizer):
  """Converts a single `InputExample` into a single `InputFeatures`."""
  # label_map = {}
  # for (i, label) in enumerate(label_list):
  #   label_map[label] = i

  entity2id = {'O': 1, 'SignSymptomMention': 2, 'Predicate': 3, 'DiseaseDisorderMention': 4, 
                            'MedicationMention': 5, 'RomanNumeralAnnotation': 6, 'AnatomicalSiteMention': 7, 
                            'FractionAnnotation': 8, 'ProcedureMention': 9, 'DATE': 10, '[SEP]':11, '[CLS]':12}

  entity_a = example.entity_a.split()
  entity_b = example.entity_b.split()
  tokens_a = example.text_a
  tokens_b = example.text_b
  retriv_a = example.retriv_a
  retriv_b = example.retriv_b
  tokens = []
  segment_ids = []
  entity_a_ids = []
  entity_b_ids = []
  entity_ids = []
  to_a = []
  to_b = []
  retriv_tokens = []
  retrieve_segment_ids  = []


  
  retriv_a_tokens = tokenizer.tokenize(retriv_a)
  retriv_b_tokens = tokenizer.tokenize(retriv_b)

  for i, token in enumerate(tokens_a.split()):
    tos = tokenizer.tokenize(token)
    for t in tos:
      to_a.append(t)
      entity_a_ids.append(entity2id[entity_a[i]])

  if tokens_b:
    for i, token in enumerate(tokens_b.split()):
      tos = tokenizer.tokenize(token)
      for t in tos:
        to_b.append(t)
        entity_b_ids.append(entity2id[entity_b[i]])


  # tokens_a = tokenizer.tokenize(example.text_a)

  # if example.text_b:
  #   tokens_b = tokenizer.tokenize(example.text_b)

  

  if tokens_b:
    # Modifies `tokens_a` and `tokens_b` in place so that the total
    # length is less than the specified length.
    # Account for [CLS], [SEP], [SEP] with "- 3"
    _truncate_seq_pair(to_a, to_b, max_seq_length - 3)
    _truncate_seq_pair(retriv_a_tokens, retriv_b_tokens, max_seq_length - 3)
    _truncate_seq_pair(entity_a_ids, entity_b_ids, max_seq_length - 3)
  else:
    # Account for [CLS] and [SEP] with "- 2"
    if len(tokens_a) > max_seq_length - 2:
      to_a = to_a[0:(max_seq_length - 2)]
      entity_a_ids = entity_a_ids[0:(max_seq_length - 2)]
    
  

  tokens.append("[CLS]")
  segment_ids.append(0)
  entity_ids =[0] + entity_a_ids + [1] + entity_b_ids + [1]
  for token in to_a:
    tokens.append(token)
    segment_ids.append(0)

  tokens.append("[SEP]")
  segment_ids.append(0)

  if tokens_b:
    for token in to_b:
      tokens.append(token)
      segment_ids.append(1)
    tokens.append("[SEP]")
    segment_ids.append(1) 

  for token in retriv_a_tokens:
    retriv_tokens.append(token)
    retrieve_segment_ids.append(0)

  retriv_tokens.append("[SEP]")
  retrieve_segment_ids.append(0)

  for token in retriv_b_tokens:
    retriv_tokens.append(token)
    retrieve_segment_ids.append(1)
  retriv_tokens.append("[SEP]")
  retrieve_segment_ids.append(1) 
  
  '''
  将ntokens转换为char 序列
  '''
  # print(ntokens)
  char_ids = []
  for item_token in tokens:
      tmp_char = list(item_token)
      ##截断
      tmp_char = tmp_char[:FLAGS.max_word_length]
      tmp_char = [str(i).lower() for i in tmp_char]
      tmp_char_tokenize = []
      for i in tmp_char:
          tmp_char_tokenize.extend(char_tokenizer.tokenize(i))
      tmp_char = tmp_char_tokenize
      tmp_char_ids = char_tokenizer.convert_tokens_to_ids(tmp_char)
      ##填充到max_word_length
      while len(tmp_char_ids) < FLAGS.max_word_length:
        tmp_char_ids.append(0)
      # print(tmp_char_ids)
      char_ids.extend(tmp_char_ids)
  # print(char_ids)
  # sys.exit(0)

  input_ids = tokenizer.convert_tokens_to_ids(tokens)
  retriv_tokens_ids = tokenizer.convert_tokens_to_ids(retriv_tokens)

  # The mask has 1 for real tokens and 0 for padding tokens. Only real
  # tokens are attended to.
  input_mask = [1] * len(input_ids)
  retrieve_mask = [1] * len(retriv_tokens_ids)

  abcnn_input_a_ids = [entity2id[i] for i in entity_a]
  abcnn_input_b_ids = [entity2id[i] for i in entity_b]



  # Zero-pad up to the sequence length.
  while len(input_ids) < max_seq_length:
    input_ids.append(0)
    input_mask.append(0)
    segment_ids.append(0)
    entity_ids.append(1) # 1 stands 'O'
    char_ids.extend([0]*FLAGS.max_word_length)

  while len(retriv_tokens_ids) < max_seq_length:
    retriv_tokens_ids.append(0)
    retrieve_mask.append(0)
    retrieve_segment_ids.append(0)
  
  similarity = get_sim(entity_ids)
  # print(len(similarity))


  # Zero-pad up to the abcnn input sequence length.
  abcnn_input_a_ids = abcnn_input_a_ids[:FLAGS.abcnn_max_seqlen]
  abcnn_input_b_ids = abcnn_input_b_ids[:FLAGS.abcnn_max_seqlen]
  while len(abcnn_input_a_ids) < FLAGS.abcnn_max_seqlen:
    abcnn_input_a_ids.append(0)
  while len(abcnn_input_b_ids) < FLAGS.abcnn_max_seqlen:
    abcnn_input_b_ids.append(0)

  # print("input_ids:", len(input_ids))
  # print("segment_ids:", len(segment_ids))
  # print("entity_ids:", len(entity_ids))

  assert len(input_ids) == max_seq_length
  assert len(input_mask) == max_seq_length
  assert len(segment_ids) == max_seq_length
  assert len(entity_ids) == max_seq_length
  assert len(char_ids) == max_seq_length*FLAGS.max_word_length
#   assert len(example.entity_a_kb) == FLAGS.entity_vec
#   assert len(example.entity_b_kb) == FLAGS.entity_vec
  assert len(abcnn_input_a_ids) == FLAGS.abcnn_max_seqlen
  assert len(abcnn_input_b_ids) == FLAGS.abcnn_max_seqlen
  assert len(similarity) == max_seq_length*max_seq_length

  label_value = float(example.label)
  if ex_index < 5:
    tf.logging.info("*** Example ***")
    tf.logging.info("guid: %s" % (example.guid))
    tf.logging.info("tokens: %s" % " ".join(
        [tokenization.printable_text(x) for x in tokens]))
    tf.logging.info("input_ids: %s" % " ".join([str(x) for x in input_ids]))
    tf.logging.info("input_mask: %s" % " ".join([str(x) for x in input_mask]))
    tf.logging.info("segment_ids: %s" % " ".join([str(x) for x in segment_ids]))
    tf.logging.info("entity_ids: %s" % " ".join([str(x) for x in entity_ids]))
    tf.logging.info("label: %s (id = %f)" % (example.label, label_value))
    tf.logging.info("similarity: %s" % " ".join([str(x) for x in similarity[:max_seq_length]]))
#     tf.logging.info("hand_fea: %s" % " ".join([str(x) for x in hand_fea]))
    # tf.logging.info("char_ids: %s" % " ".join([str(x) for x in char_ids]))
#     tf.logging.info("entity_a_kb: %s" % " ".join([str(x) for x in example.entity_a_kb]))
#     tf.logging.info("entity_b_kb: %s" % " ".join([str(x) for x in example.entity_b_kb]))
    tf.logging.info("abcnn_input_a_ids: %s" % " ".join([str(x) for x in abcnn_input_a_ids]))
    tf.logging.info("abcnn_input_b_ids: %s" % " ".join([str(x) for x in abcnn_input_b_ids]))
    tf.logging.info("retriv_tokens_ids: %s" % " ".join([str(x) for x in retriv_tokens_ids]))
    tf.logging.info("retrieve_mask: %s" % " ".join([str(x) for x in retrieve_mask]))
    tf.logging.info("retrieve_segment_ids: %s" % " ".join([str(x) for x in retrieve_segment_ids]))


  feature = InputFeatures(
      input_ids=input_ids,
      input_mask=input_mask,
      segment_ids=segment_ids,
      entity_ids=entity_ids,
      label_value=label_value,
      hand_fea=example.hand_fea,
      char_ids=char_ids,
      entity_a=abcnn_input_a_ids,
      entity_b=abcnn_input_b_ids,
      entity_a_kb=example.entity_a_kb,
      entity_b_kb=example.entity_b_kb,
      similarity=similarity,
      retriv_tokens_ids=retriv_tokens_ids,
      retrieve_segment_ids=retrieve_segment_ids,
      retrieve_mask=retrieve_mask)
  return feature


def file_based_convert_examples_to_features(
    examples, label_list, max_seq_length, tokenizer, char_tokenizer, output_file):
  """Convert a set of `InputExample`s to a TFRecord file."""

  writer = tf.python_io.TFRecordWriter(output_file)

  for (ex_index, example) in enumerate(examples):
    if ex_index % 10000 == 0:
      tf.logging.info("Writing example %d of %d" % (ex_index, len(examples)))

    feature = convert_single_example(ex_index, example, label_list,
                                     max_seq_length, tokenizer, char_tokenizer)

    def create_int_feature(values):
      f = tf.train.Feature(int64_list=tf.train.Int64List(value=list(values)))
      return f

    def create_float_feature(values):
      f = tf.train.Feature(float_list=tf.train.FloatList(value=list(values)))
      return f

    features = collections.OrderedDict()
    
    features["input_ids"] = create_int_feature(feature.input_ids)
    features["input_mask"] = create_int_feature(feature.input_mask)  
    features["segment_ids"] = create_int_feature(feature.segment_ids)
    features["entity_ids"] = create_int_feature(feature.entity_ids)
    ##TODO
#     features["hand_fea"] = create_float_feature(feature.hand_fea)
    features["char_ids"] = create_int_feature(feature.char_ids)
#     features["entity_a_kb"] = create_float_feature(feature.entity_a_kb)
#     features["entity_b_kb"] = create_float_feature(feature.entity_b_kb)
    features["entity_a"] = create_int_feature(feature.entity_a)
    features["entity_b"] = create_int_feature(feature.entity_b)
    features["label_values"] = create_float_feature([feature.label_value])
    features["similarity"] = create_int_feature(feature.similarity)
    features["retriv_tokens_ids"] = create_int_feature(feature.retriv_tokens_ids)
    features["retrieve_segment_ids"] = create_int_feature(feature.retrieve_segment_ids)
    features["retrieve_mask"] = create_int_feature(feature.retrieve_mask)

    tf_example = tf.train.Example(features=tf.train.Features(feature=features))
    writer.write(tf_example.SerializeToString())


def file_based_input_fn_builder(input_file, seq_length, is_training,
                                drop_remainder,hand_fea_len=29):
  """Creates an `input_fn` closure to be passed to TPUEstimator."""

  name_to_features = {
      "input_ids": tf.FixedLenFeature([seq_length], tf.int64),
      "input_mask": tf.FixedLenFeature([seq_length], tf.int64),
      "segment_ids": tf.FixedLenFeature([seq_length], tf.int64),
      "entity_ids": tf.FixedLenFeature([seq_length], tf.int64),
      "label_values": tf.FixedLenFeature([], tf.float32),
#       "hand_fea": tf.FixedLenFeature([hand_fea_len], tf.float32),
      "char_ids": tf.FixedLenFeature([seq_length*FLAGS.max_word_length], tf.int64),
#       "entity_a_kb": tf.FixedLenFeature([FLAGS.entity_vec], tf.float32),
#       "entity_b_kb": tf.FixedLenFeature([FLAGS.entity_vec], tf.float32),
      "entity_a": tf.FixedLenFeature([FLAGS.abcnn_max_seqlen], tf.int64),
      "entity_b": tf.FixedLenFeature([FLAGS.abcnn_max_seqlen], tf.int64),
      "similarity": tf.FixedLenFeature([seq_length*seq_length], tf.int64),
      "retriv_tokens_ids": tf.FixedLenFeature([seq_length], tf.int64),
      "retrieve_segment_ids": tf.FixedLenFeature([seq_length], tf.int64),
      "retrieve_mask": tf.FixedLenFeature([seq_length], tf.int64),
  
  }

  def _decode_record(record, name_to_features):
    """Decodes a record to a TensorFlow example."""
    example = tf.parse_single_example(record, name_to_features)

    # tf.Example only supports tf.int64, but the TPU only supports tf.int32.
    # So cast all int64 to int32.
    for name in list(example.keys()):
      t = example[name]
      if t.dtype == tf.int64:
        t = tf.to_int32(t)
      example[name] = t

    return example

  def input_fn(params):
    """The actual input function."""
    batch_size = params["batch_size"]

    # For training, we want a lot of parallel reading and shuffling.
    # For eval, we want no shuffling and parallel reading doesn't matter.
    d = tf.data.TFRecordDataset(input_file)
    if is_training:
      d = d.repeat()
      d = d.shuffle(buffer_size=100)

    d = d.apply(
        tf.contrib.data.map_and_batch(
            lambda record: _decode_record(record, name_to_features),
            batch_size=batch_size,
            drop_remainder=drop_remainder))

    return d

  return input_fn


def _truncate_seq_pair(tokens_a, tokens_b, max_length):
  """Truncates a sequence pair in place to the maximum length."""

  # This is a simple heuristic which will always truncate the longer sequence
  # one token at a time. This makes more sense than truncating an equal percent
  # of tokens from each, since if one sequence is very short then each token
  # that's truncated likely contains more information than a longer sequence.
  while True:
    total_length = len(tokens_a) + len(tokens_b)
    if total_length <= max_length:
      break
    if len(tokens_a) > len(tokens_b):
      tokens_a.pop()
    else:
      tokens_b.pop()


def create_model(bert_config, is_training, input_ids, char_ids, input_mask, segment_ids, entity_ids,
                 labels, similarity, retriv_tokens_ids, retrieve_segment_ids, retrieve_mask, num_labels, use_one_hot_embeddings,hand_fea,entity_a,entity_b,\
                   entity_a_kb,entity_b_kb):
  """Creates a classification model."""
  # print(similarity)
  model = modeling_modif.BertModel(
      config=bert_config,
      is_training=is_training,
      input_ids=input_ids,
      input_mask=input_mask,
      token_type_ids=segment_ids,
      entity_ids=entity_ids,
      use_one_hot_embeddings=use_one_hot_embeddings,
      similarity=similarity)
  
  model_retrieve = modeling_modif.BertModel(
      config=bert_config,
      is_training=is_training,
      input_ids=retriv_tokens_ids,
      input_mask=retrieve_mask,
      token_type_ids=retrieve_segment_ids,
      entity_ids=None,
      use_one_hot_embeddings=use_one_hot_embeddings,
      similarity=None)

  # sys.exit(0)
  # In the demo, we are doing a simple classification task on the entire
  # segment.
  #
  # If you want to use the token-level output, use model.get_sequence_output()
  # instead.
  output_layer = model.get_pooled_output()
  output_layer_retrieve = model_retrieve.get_pooled_output()
  all_output = model.get_sequence_output()
  aug_loss = model.get_aug_loss()
  # print(aug_loss)
  
  '''
  ABCNN BERT
  '''
  
# get the encoded rep from ABCNN
  with tf.variable_scope('abcnn_embedding'):
    abcnn_embedding = tf.get_variable("abcnn_embedding", shape=[11, 50],
                        dtype=tf.float32, initializer=initializers.xavier_initializer())
    # print(entity_a)
    # print(entity_b)
    abcnn_input_a_ids_embed = tf.nn.embedding_lookup(abcnn_embedding,entity_a)
    abcnn_input_b_ids_embed = tf.nn.embedding_lookup(abcnn_embedding,entity_b)
    abcnn_input_a_ids_embed = tf.transpose(abcnn_input_a_ids_embed,perm=[0,2,1])
    abcnn_input_b_ids_embed = tf.transpose(abcnn_input_b_ids_embed,perm=[0,2,1])
  abcnn_model = ABCNN.ABCNN(abcnn_input_a_ids_embed,abcnn_input_b_ids_embed,labels)
  encode_rep = abcnn_model.get_encode_rep()
  # encode_rep = tf.tanh(encode_rep)
  # print('====='*20)
  # print(encode_rep)
  

  '''
  char model
  '''
  ## add character-level-embedding
  char_ids = tf.reshape(char_ids,shape=[-1,FLAGS.max_word_length])
  print(char_ids.shape)
  with tf.variable_scope('char_embedding'):
      char_embedding = tf.get_variable("char_embedding", shape=[FLAGS.char_vocab_size, FLAGS.char_embed_dim],
                          dtype=tf.float32, initializer=initializers.xavier_initializer())

      embed_char = tf.nn.embedding_lookup(char_embedding,char_ids)
  print(embed_char.shape)
  with tf.variable_scope('char_CNN'):
      cnn_embed_char = tf.layers.Conv1D(filters=FLAGS.char_embed_dim,kernel_size=3,padding='same',activation='tanh',strides=2)(embed_char)
      pool_size = char_embedding.get_shape().as_list()[1]
      print(cnn_embed_char)
      char_pool = tf.layers.MaxPooling1D(pool_size=pool_size, strides=pool_size, padding='same')(cnn_embed_char)
      print(char_pool)
      char_rep = tf.reshape(char_pool,shape=[-1,FLAGS.max_seq_length,FLAGS.char_embed_dim])
      print(char_rep)
      char_max_rep = tf.layers.MaxPooling1D(pool_size=FLAGS.max_seq_length, strides=FLAGS.max_seq_length, padding='same')(char_rep)
      print(char_max_rep)
      char_avg_rep = tf.layers.AveragePooling1D(pool_size=FLAGS.max_seq_length, strides=FLAGS.max_seq_length, padding='same')(char_rep)
      print(char_avg_rep)


  hidden_size = output_layer.shape[-1].value

  # output_weights_1 = tf.get_variable(
  #     "weights_1", [hidden_size//2, hidden_size],
  #     initializer=tf.truncated_normal_initializer(stddev=0.02))

  # output_bias_1 = tf.get_variable(
  #     "bias_1", [hidden_size//2], initializer=tf.zeros_initializer())

  output_weights_2 = tf.get_variable(
      "oweights_2", [1, hidden_size],
      initializer=tf.truncated_normal_initializer(stddev=0.02))

  output_bias_2 = tf.get_variable(
      "bias_2", [1], initializer=tf.zeros_initializer())
  

  with tf.variable_scope("loss"):  
    if is_training == True:
      output_layer = tf.nn.dropout(output_layer, 0.9)
      output_layer_retrieve = tf.nn.dropout(output_layer_retrieve, 0.9)

    # logits = tf.matmul(output_layer, output_weights_1, transpose_b=True)
    # logits = tf.nn.bias_add(logits, output_bias_1)
    # logits = tf.nn.relu(logits)
    logits = tf.matmul(output_layer, output_weights_2, transpose_b=True)
    logits = tf.nn.bias_add(logits, output_bias_2)

    logits = tf.nn.relu(logits)
    logits = tf.squeeze(logits)

    # logits_retrieve = tf.matmul(output_layer_retrieve, output_weights_1, transpose_b=True)
    # logits_retrieve = tf.nn.bias_add(logits_retrieve, output_bias_1)
    # logits_retrieve = tf.nn.relu(logits_retrieve)
    logits_retrieve = tf.matmul(output_layer_retrieve, output_weights_2, transpose_b=True)
    logits_retrieve = tf.nn.bias_add(logits_retrieve, output_bias_2)

    logits_retrieve = tf.nn.relu(logits_retrieve)
    logits_retrieve = tf.squeeze(logits_retrieve)

    logits = logits 
    pred = logits
  #   #loss = tf.losses.huber_loss(labels,logits)

    # loss = tf.losses.mean_squared_error(labels,logits+logits_retrieve)
    loss = tf.losses.mean_squared_error(labels,logits)

    # return loss+0.1*aug_loss,pred
    return loss,pred


def model_fn_builder(bert_config, num_labels, init_checkpoint, learning_rate, other_learning_rate,
                     num_train_steps, num_warmup_steps, use_tpu,
                     use_one_hot_embeddings):
  """Returns `model_fn` closure for TPUEstimator."""

  def model_fn(features, labels, mode, params):  # pylint: disable=unused-argument
    """The `model_fn` for TPUEstimator."""
    nonlocal num_train_steps
    tf.logging.info("*** Features ***")
    for name in sorted(features.keys()):
      tf.logging.info("  name = %s, shape = %s" % (name, features[name].shape))

    input_ids = features["input_ids"]
    input_mask = features["input_mask"]
    segment_ids = features["segment_ids"]
    entity_ids = features["entity_ids"]
    label_values = features["label_values"]
#     hand_fea = features["hand_fea"]
    char_ids = features["char_ids"]
    entity_a = features["entity_a"]
    entity_b = features["entity_b"]
#     entity_a_kb = features["entity_a_kb"]
#     entity_b_kb = features["entity_b_kb"]
    similarity = features["similarity"]
    retriv_tokens_ids = features["retriv_tokens_ids"]
    retrieve_segment_ids = features["retrieve_segment_ids"]
    retrieve_mask = features["retrieve_mask"]

    is_training = (mode == tf.estimator.ModeKeys.TRAIN)

    total_loss, pred= create_model(
        bert_config, is_training, input_ids, char_ids, input_mask, segment_ids, entity_ids, label_values, similarity, retriv_tokens_ids,
        retrieve_segment_ids, retrieve_mask, num_labels, use_one_hot_embeddings,hand_fea=None,entity_a=entity_a,entity_b=entity_b,entity_a_kb=None,entity_b_kb=None)

    tvars = tf.trainable_variables()
    initialized_variable_names = {}
    scaffold_fn = None
    if init_checkpoint:
      (assignment_map, initialized_variable_names
      ) = modeling_modif.get_assignment_map_from_checkpoint(tvars, init_checkpoint)
      if use_tpu:

        def tpu_scaffold():
          tf.train.init_from_checkpoint(init_checkpoint, assignment_map)
          return tf.train.Scaffold()

        scaffold_fn = tpu_scaffold
      else:
        tf.train.init_from_checkpoint(init_checkpoint, assignment_map)

    tf.logging.info("**** Trainable Variables ****")
    for var in tvars:
      init_string = ""
      if var.name in initialized_variable_names:
        init_string = ", *INIT_FROM_CKPT*"
      tf.logging.info("  name = %s, shape = %s%s", var.name, var.shape,
                      init_string)

    output_spec = None
    if mode == tf.estimator.ModeKeys.TRAIN:

      if FLAGS.do_train_and_eval:
        print('*****************Do train and eval******************')
        num_train_steps = int(num_train_steps/FLAGS.num_train_epochs*FLAGS.max_train_epochs)
        num_warmup_steps = int(num_train_steps*FLAGS.warmup_proportion)

      train_op = optimization.create_optimizer(
          total_loss, learning_rate, other_learning_rate, num_train_steps, num_warmup_steps, use_tpu)
      
      logging_hook = tf.train.LoggingTensorHook({"train_loss": total_loss}, every_n_iter=20)
      output_spec = tf.contrib.tpu.TPUEstimatorSpec(
          mode=mode,
          loss=total_loss,
          train_op=train_op,
          training_hooks=[logging_hook],
          scaffold_fn=scaffold_fn)
    elif mode == tf.estimator.ModeKeys.EVAL:
      # logging_hook = tf.train.LoggingTensorHook({"eval_loss": total_loss}, every_n_iter=20)

      output_spec = tf.contrib.tpu.TPUEstimatorSpec(
          mode=mode, predictions=pred, scaffold_fn=scaffold_fn)
    else:
      # logging_hook = tf.train.LoggingTensorHook({"test_loss": total_loss}, every_n_iter=20)

      output_spec = tf.contrib.tpu.TPUEstimatorSpec(
          mode=mode, predictions=pred, scaffold_fn=scaffold_fn)
    return output_spec

  return model_fn

def main(_):
  tf.logging.set_verbosity(tf.logging.INFO)

  processors = {  
      "textsim": TextsimProcessor
  }

  if not FLAGS.do_train and not FLAGS.do_eval and not FLAGS.do_predict:
    raise ValueError(
        "At least one of `do_train`, `do_eval` or `do_predict' must be True.")

  bert_config = modeling_modif.BertConfig.from_json_file(FLAGS.bert_config_file)

  if FLAGS.max_seq_length > bert_config.max_position_embeddings:
    raise ValueError(
        "Cannot use sequence length %d because the BERT model "
        "was only trained up to sequence length %d" %
        (FLAGS.max_seq_length, bert_config.max_position_embeddings))

  tf.gfile.MakeDirs(FLAGS.output_dir)

  task_name = FLAGS.task_name.lower()

  if task_name not in processors:
    raise ValueError("Task not found: %s" % (task_name))

  processor = processors[task_name]()

  label_list = processor.get_labels()

  char_tokenizer = tokenization.FullTokenizer(
        vocab_file=FLAGS.char_vocab_file, do_lower_case=FLAGS.do_lower_case)

  tokenizer = tokenization.FullTokenizer(
      vocab_file=FLAGS.vocab_file, do_lower_case=FLAGS.do_lower_case)

  tpu_cluster_resolver = None
  if FLAGS.use_tpu and FLAGS.tpu_name:
    tpu_cluster_resolver = tf.contrib.cluster_resolver.TPUClusterResolver(
        FLAGS.tpu_name, zone=FLAGS.tpu_zone, project=FLAGS.gcp_project)

  is_per_host = tf.contrib.tpu.InputPipelineConfig.PER_HOST_V2
  run_config = tf.contrib.tpu.RunConfig(
      cluster=tpu_cluster_resolver,
      master=FLAGS.master,
      model_dir=FLAGS.output_dir,
      save_checkpoints_steps=FLAGS.save_checkpoints_steps,
      tpu_config=tf.contrib.tpu.TPUConfig(
          iterations_per_loop=FLAGS.iterations_per_loop,
          num_shards=FLAGS.num_tpu_cores,
          per_host_input_for_training=is_per_host))

  train_examples = None
  num_train_steps = None
  num_warmup_steps = None
  if FLAGS.do_train:
    train_examples = processor.get_train_examples(FLAGS.data_dir, FLAGS.retrieve_dir)
    train_examples = train_examples[:800]
    num_train_steps = int(
        len(train_examples) / FLAGS.train_batch_size * FLAGS.num_train_epochs)
    num_warmup_steps = int(num_train_steps * FLAGS.warmup_proportion)

  model_fn = model_fn_builder(
      bert_config=bert_config,
      num_labels=len(label_list),
      init_checkpoint=FLAGS.init_checkpoint,
      learning_rate=FLAGS.learning_rate,
      other_learning_rate=FLAGS.other_learning_rate,
      num_train_steps=num_train_steps,
      num_warmup_steps=num_warmup_steps,
      use_tpu=FLAGS.use_tpu,
      use_one_hot_embeddings=FLAGS.use_tpu)

  # If TPU is not available, this will fall back to normal Estimator on CPU
  # or GPU.
  estimator = tf.contrib.tpu.TPUEstimator(
      use_tpu=FLAGS.use_tpu,
      model_fn=model_fn,
      config=run_config,
      train_batch_size=FLAGS.train_batch_size,
      eval_batch_size=FLAGS.eval_batch_size,
      predict_batch_size=FLAGS.predict_batch_size)

  if FLAGS.do_train:
    train_file = os.path.join(FLAGS.output_dir, "train.tf_record")
    train_examples = train_examples[:800]
    print(len(train_examples))
    file_based_convert_examples_to_features(
        train_examples, label_list, FLAGS.max_seq_length, tokenizer, char_tokenizer, train_file)
    tf.logging.info("***** Running training *****")
    tf.logging.info("  Num examples = %d", len(train_examples))
    tf.logging.info("  Batch size = %d", FLAGS.train_batch_size)
    tf.logging.info("  Num steps = %d", num_train_steps)
    train_input_fn = file_based_input_fn_builder(
        input_file=train_file,
        seq_length=FLAGS.max_seq_length,
        is_training=True,
        drop_remainder=True)
    estimator.train(input_fn=train_input_fn, max_steps=num_train_steps)

  if FLAGS.do_eval:
    eval_examples = processor.get_dev_examples(FLAGS.data_dir, FLAGS.retrieve_dir)
    eval_examples = eval_examples[800:]
    eval_file = os.path.join(FLAGS.output_dir, "eval.tf_record")
    file_based_convert_examples_to_features(
        eval_examples, label_list, FLAGS.max_seq_length, tokenizer, char_tokenizer, eval_file)

    tf.logging.info("***** Running evaluation *****")
    tf.logging.info("  Num examples = %d", len(eval_examples))
    tf.logging.info("  Batch size = %d", FLAGS.eval_batch_size)

    # This tells the estimator to run through the entire set.
    eval_steps = None
    # However, if running eval on the TPU, you will need to specify the
    # number of steps.
    if FLAGS.use_tpu:
      # Eval will be slightly WRONG on the TPU because it will truncate
      # the last batch.
      eval_steps = int(len(eval_examples) / FLAGS.eval_batch_size)

    eval_drop_remainder = True if FLAGS.use_tpu else False
    eval_input_fn = file_based_input_fn_builder(
        input_file=eval_file,
        seq_length=FLAGS.max_seq_length,
        is_training=False,
        drop_remainder=eval_drop_remainder)

    result = estimator.predict(input_fn=eval_input_fn)
    # f = open(os.path.join(FLAGS.data_dir, "dev_result.out"), 'w')
    results = []
    i=0
    result = list(result)
    for r in result:
      if float(r) > 5.0:
        r = 5.0
      if float(r) < 0.0:
        r = 0.0
      # i+=1
      # print(i)
      # print(r)
      results.append(str(r))
      # print('******')
    # print(result)
    # result = list(result)
    #   f.write(str(r))
    #   f.write('\n')
          
    # #   results.append(r)
    # #   print(r)
    # results = open(os.path.join(FLAGS.data_dir, "dev_result.out"), 'r').read().split('\n')
    # print('预测结果为：',results)
    gold = []
    with open(os.path.join(FLAGS.data_dir, "all_kg.txt"), 'r') as f:
      lines = f.readlines()
      lines = lines[800:]
      for line in lines:
        
        tmp = line.strip('\n').split('\t')[-1]
        
        gold.append(tmp)
    # print('gold label：',gold)
    results = np.array(results).astype(float)
    print(results)
    gold = np.array(gold).astype(float)
    dev_pearson = np.corrcoef(result,gold)[0][1]
    print('验证集皮尔逊系数为: ',dev_pearson)

  if FLAGS.do_predict:
    predict_examples = processor.get_test_examples(FLAGS.data_dir, FLAGS.retrieve_dir)
    predict_examples = predict_examples[800:]
    predict_file = os.path.join(FLAGS.output_dir, "predict.tf_record")
    file_based_convert_examples_to_features(predict_examples, label_list,
                                            FLAGS.max_seq_length, tokenizer, char_tokenizer,
                                            predict_file)

    tf.logging.info("***** Running prediction*****")
    tf.logging.info("  Num examples = %d", len(predict_examples))
    tf.logging.info("  Batch size = %d", FLAGS.predict_batch_size)

    if FLAGS.use_tpu:
      # Warning: According to tpu_estimator.py Prediction on TPU is an
      # experimental feature and hence not supported here
      raise ValueError("Prediction in TPU not supported")

    predict_drop_remainder = True if FLAGS.use_tpu else False
    predict_input_fn = file_based_input_fn_builder(
        input_file=predict_file,
        seq_length=FLAGS.max_seq_length,
        is_training=False,
        drop_remainder=predict_drop_remainder)

    result = estimator.predict(input_fn=predict_input_fn)
    # result = np.array(list(result))
    # np.save('EBMSASS_train_biobert_re_ea', result)
    
    result_xy = []
    for r in result:
      if float(r) > 5.0:
        r = 5.0
      if float(r) < 0.0:
        r = 0.0
      result_xy.append(np.float(r))
    
    with open(os.path.join(FLAGS.output_dir,'test_result.txt'),'w') as f:
      for tmp_result in result_xy:
        f.write(str(tmp_result) + '\n')
    # with open('result.txt','a') as f:
    #     f.write('===============华丽的分隔符===============')
    #     f.write('\n')
    # joblib.dump(np.array(results),os.path.join(FLAGS.data_dir, 'bert_result_test.pkl'))
    # print('预测结果为：',result)
      gold = []
      with open(os.path.join(FLAGS.data_dir, "all_kg.txt"), 'r') as f1:
      # with open('/disk2/xy_disk2/thesis/STS/LAP/data/2019n2c2/test_data/test_kg.txt', 'r') as f1:
        lines = f1.readlines()
        lines = lines[800:]
        for line in lines:
          tmp = float(line.strip('\n').split('\t')[-1])
          gold.append(tmp)

        test_pearson = np.corrcoef(np.array(result_xy).astype(float),np.array(gold).astype(float))[0][1]
        test_spearman = scipy.stats.spearmanr(result_xy, gold)[0]
        print('测试集皮尔逊系数为: ',test_pearson)
        f.write('test pearson: ' + str(test_pearson) + '\n')
        print('测试集spearmanr系数为: ',test_spearman)
        f.write('test spearmanr: ' + str(test_spearman))
    
if __name__ == "__main__":
  flags.mark_flag_as_required("data_dir")
  flags.mark_flag_as_required("task_name")
  flags.mark_flag_as_required("vocab_file")
  flags.mark_flag_as_required("bert_config_file")
  flags.mark_flag_as_required("output_dir")
  tf.app.run()
