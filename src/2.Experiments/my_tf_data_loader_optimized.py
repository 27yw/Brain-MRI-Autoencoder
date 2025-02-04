import tensorflow as tf
import tensorflow_addons as tfa


class tf_data_png_loader():
    def __init__(self, files_path, batch_size=8, cache=False, shuffle_buffer_size=1000, resize=(128,128), train=True, augment=False):
        self.files_path = files_path
        self.samples = len(self.files_path)
        self.batch_size = batch_size
        self.cache = cache
        self.shuffle_buffer_size = shuffle_buffer_size
        self.resize = resize
        self.train = train
        self.augment = augment
        
    def get_tf_ds_generator(self):
        """
        Load the images in batches using Tensorflow (tfdata).
        Cache can be used to speed up the process.
        Faster method in comparison to image loading using Keras.
        Returns:
        Data Generator to be used while training the model.
        https://towardsdatascience.com/dump-keras-imagedatagenerator-start-using-tensorflow-tf-data-part-2-fba7cda81203
        """
        def parse_image(file_path):
            # load the raw data from the file as a string
            img = tf.io.read_file(file_path)
            # convert the compressed string to a 3D float tensor
            img = tf.io.decode_png(img, channels=1)
            img = tf.image.convert_image_dtype(img, tf.float32)
            
            if self.resize and self.resize !=(256,256):
                img = tf.image.resize(img, self.resize)
            
            #min_max_sacler_norm
            img = tf.math.divide(tf.math.subtract(img, tf.math.reduce_min(img)),
                                 tf.math.subtract(tf.math.reduce_max(img), tf.math.reduce_min(img)))
            #std_norm
            #img = tf.math.divide(tf.math.subtract(img, tf.math.reduce_mean(img)),tf.math.reduce_std(img))
            return img, tf.identity(img)


        def prepare_for_training(ds, cache=False, shuffle_buffer_size=10000):
            # If a small dataset, only load it once, and keep it in memory.
            # use `.cache(filename)` to cache preprocessing work for datasets that don't fit in memory.
            if cache:
                if isinstance(cache, str):
                    ds = ds.cache(cache)
                else:
                    ds = ds.cache()

            if self.train:
                #https://stackoverflow.com/questions/46444018/meaning-of-buffer-size-in-dataset-map-dataset-prefetch-and-dataset-shuffle
                ds = ds.shuffle(buffer_size=shuffle_buffer_size)

            # representing the number of times the dataset should be repeated. 
            # The default behavior (if count is None or -1) is for the dataset be repeated indefinitely.
            if self.train:
                ds = ds.repeat()
            
            if self.augment:
                ds = ds.map(self.img_augment, num_parallel_calls=AUTOTUNE)
            
            ds = ds.batch(self.batch_size)
            
            #HERE AUGMENTATION works on batches
            #aug_ds = train_ds.map(lambda x, y: (resize_and_rescale(x, training=True), y))

            if self.train:
                # `prefetch` lets the dataset fetch batches in the background while the model is training.
                ds = ds.prefetch(buffer_size=AUTOTUNE)
            return ds

        #Get all path files
        ds = tf.data.Dataset.from_tensor_slices(self.files_path)

        # Set `num_parallel_calls` so that multiple images are processed in parallel
        AUTOTUNE = tf.data.experimental.AUTOTUNE
        ds = ds.map(parse_image, num_parallel_calls=AUTOTUNE)

        # cache = True, False, './file_name'
        # If the dataset doesn't fit in memory use a cache file,eg. cache='./data.tfcache'
        return prepare_for_training(ds, cache=self.cache, shuffle_buffer_size = self.shuffle_buffer_size) #'cocodata.tfcache'


    def img_augment(self, image, label):    
    
        #Noise and Dropout
        rnds_noise = tf.random.uniform((1,2),minval=0, maxval=0.04)
        image = tf.nn.dropout(image,rnds_noise[0][0])
        image = tf.keras.layers.GaussianNoise(rnds_noise[0][1])(image, training=True)
        
        #Blankout and blur
        rnds_absolutes = tf.random.uniform((1,2),minval=0, maxval=1)
        if rnds_absolutes[0][0] < 0.2:
            size = tf.random.uniform((), minval=10, maxval=40, dtype=tf.dtypes.int32)
            offset = tf.random.uniform((), minval=10, maxval=100, dtype=tf.dtypes.int32)
            image = tfa.image.cutout(tf.expand_dims(image,0),  
                                    mask_size = (size,size ),
                                    offset = (offset, offset),
                                    constant_values = 0
                                    )[0,...]
        if rnds_absolutes[0][1] < 0.1:
            image = tfa.image.gaussian_filter2d(image,
                                                filter_shape = [3, 3],
                                                sigma = 0.6,
                                                constant_values = 0,
                                            )
        # Normalization
        image = tf.math.divide(tf.math.subtract(image, tf.math.reduce_min(image)),
                                    tf.math.subtract(tf.math.reduce_max(image), tf.math.reduce_min(image)))
        return image, label
    
