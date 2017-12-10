# encoding=utf-8

import tensorflow as tf

class TextCNN(object):
    """
    CNN 文本分类的网络构建
    包括embedding layer, Convolutional layer max-pooling, softmax layer
    """

    def __init__(self, seq_length, num_classes, vocab_size, embedding_size, filter_sizes, num_filters,
                 l2_reg_lambda=0.0):
        """

        :param seq_length: 
        :param num_classes: 
        :param vocab_size: 
        :param embedding_size: 
        :param filter_sizes: 
        :param num_filters: 
        :param l2_reg_lambda: 
        """
        # 定义输入，输出，和dropout的参数
        # [样本个数，每个样本的词个数]
        self.input_x = tf.placeholder(tf.int32, [None, seq_length], name='input_x')
        # [样本个数， 类别个数]
        self.input_y = tf.placeholder(tf.float32, [None, num_classes], name='input_y')
        # dropout probability
        self.dropout_keep_prob = tf.placeholder(tf.float32, name='dropout_keep_prob')

        # l2 正则 损失
        l2_loss = tf.constant(0.0)

        # embedding layer
        with tf.device('/cpu:0'), tf.name_scope('embedding'):
            # embedding 权重
            self.W = tf.Variable(
                tf.random_uniform([vocab_size, embedding_size], -1., 1.),
                name="W")
            # look_up embedding 后得到一个三维的tensor [None,seq_length, embedding_size]
            self.embedded_chars = tf.nn.embedding_lookup(self.W, self.input_x)
            # 将embedded_chars 向量扩充一维成一个四维向量[None,seq_length, embedding_size, 1] ,这是卷积核
            self.embedded_chars_expanded = tf.expand_dims(self.embedded_chars, -1)

        # 卷积操作和最大池化操作
        pooled_output = []
        for i, filter_size in enumerate(filter_sizes):
            with tf.name_scope('conv-maxpool-%s' % filter_size):
                # 卷积层
                # 卷积核的维度
                filter_shape = [filter_size, embedding_size, 1, num_filters]
                W = tf.Variable(tf.truncated_normal(filter_shape, stddev=0.1), name="W")
                b = tf.Variable(tf.constant(0.1, shape=[num_filters]), name='b')
                conv = tf.nn.conv2d(self.embedded_chars_expanded,
                                    W,
                                    strides=[1, 1, 1, 1],
                                    padding='VALID',
                                    name='conv'
                                    )
                # 使用ReLU非线性激活函数得到一个feature map
                h = tf.nn.relu(tf.nn.bias_add(conv, b), name='relu')

                # 对刚才卷积生成的feature map 进行max-pooling，得到最大的
                pooled = tf.nn.max_pool(h,
                                        ksize=[1, seq_length - filter_size + 1, 1, 1],  # 池化窗口大小 第二个参数的意思height
                                        # 直接对featrue map 的所有进行查找最大值
                                        strides=[1, 1, 1, 1],  # 窗口在每一个维度上滑动的步长
                                        padding='VALID',
                                        name='pool')
                # 当前filter 的feature maps的池化结果拼到一起
                pooled_output.append(pooled)

        # 组合所有的feature maps 的池化结果，总个数一共是filter_size * 不同filter的个数
        # 卷积核的总个数
        num_filters_total = num_filters * len(filter_sizes)
        self.h_pool = tf.concat(pooled_output, 3)
        self.h_pool_flat = tf.reshape(self.h_pool, [-1, num_filters_total])

        # dropout layer
        with tf.name_scope('dropout'):
            self.h_drop = tf.nn.dropout(self.h_pool_flat, self.dropout_keep_prob)

        # 计算输出的概率
        with tf.name_scope('output'):
            W = tf.get_variable('W',
                                shape=[num_filters_total, num_classes],  #
                                initializer=tf.contrib.layers.xavier_initializer())
            b = tf.Variable(tf.constant(0.1, shape=[num_classes], name='b'))
            l2_loss += tf.nn.l2_loss(W)
            l2_loss += tf.nn.l2_loss(b)

            self.scores = tf.nn.xw_plus_b(self.h_drop, W, b, name='scores')
            # 找到概率最大的类别
            self.predictions = tf.argmax(self.scores, 1, name='predictons')

        # 计算损失
        with tf.name_scope('loss'):
            # 计算交叉熵损失
            losses = tf.nn.softmax_cross_entropy_with_logits(logits=self.scores, labels=self.input_y)
            # 总共的损失为交叉熵均值 和 l2正则损失
            self.loss = tf.reduce_mean(losses) + l2_loss * l2_reg_lambda

        # 计算正确率
        with tf.name_scope('accuracy'):
            correct_predictions = tf.equal(self.predictions, tf.argmax(self.input_y, 1))
            self.accuracy = tf.reduce_mean(tf.cast(correct_predictions, tf.float32), name='accuracy')