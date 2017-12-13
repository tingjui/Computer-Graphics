import sys
import os
import numpy as np
from PIL import Image
from time import time
from multiprocessing import Process, Queue, cpu_count


TILE_SIZE = 50           #the edge of mosaic tiles(square-shape) in pixels
TILE_MATCH_SIZE = 5     #the actual matching resolution (the higher the better the final result is, but need more time)
ENLARGEMENT    = 8		# the mosaic image will be this many times wider and taller than the original


TILE_BLOCK_SIZE = TILE_SIZE / max(min(TILE_MATCH_SIZE, TILE_SIZE), 1)
WORKER_COUNT = max(cpu_count() - 1, 1)
OUT_FILE_NAME = 'mosaic.jpeg'
QUEUE_EMPTY_VALUE = None	

class TileProcessor:
	def __init__(self, tiles_directory):
		self.tiles_directory = tiles_directory
	
	def __process_tile(self, tile_path):
		img = Image.open(tile_path)
		w = img.size[0]
		h = img.size[1]
		min_edge = min(w, h)
		w_crop = (w - min_edge) / 2
		h_crop = (h - min_edge) / 2
		img = img.crop((w_crop, h_crop, w - w_crop, h - h_crop))
		
		large_tile = img.resize((TILE_SIZE, TILE_SIZE), Image.ANTIALIAS)
		small_tile = img.resize((TILE_SIZE/TILE_BLOCK_SIZE, TILE_SIZE/TILE_BLOCK_SIZE), Image.ANTIALIAS)

		return (large_tile.convert('RGB'), small_tile.convert('RGB'))
		
	def get_tiles(self):	
		large_tiles = []
		small_tiles = []
		
		print('Get tile images from \'%s\'' % (self.tiles_directory))
		
		for root, subfolders, files in os.walk(self.tiles_directory):
			for tile_name in files:
				tile_path = os.path.join(root, tile_name)
				large_tile, small_tile = self.__process_tile(tile_path)
				
				large_tiles.append(large_tile)
				small_tiles.append(small_tile)
				
		print('Totally processed %d tiles' % len(large_tiles))
		
		return (large_tiles, small_tiles)
	
	
class TargetImageProcessor:
	def __init__(self, targetimage_directory):
		self.targetimage_directory = targetimage_directory
	
	def get_processed_targetimage(self):
		print 'Processing main image...'
		img = Image.open(self.targetimage_directory)
		w = img.size[0] * ENLARGEMENT
		h = img.size[1] * ENLARGEMENT
		
		large_target_image = img.resize((w,h), Image.ANTIALIAS)
		
		w_residual = (w % TILE_SIZE) / 2
		h_residual = (h % TILE_SIZE) / 2 
		
		if w_residual != 0 or h_residual != 0:
			large_target_image = large_target_image.crop((w_residual, h_residual, w-w_residual, h-h_residual))
		
		small_target_image = large_target_image.resize((w/TILE_BLOCK_SIZE, h/TILE_BLOCK_SIZE), Image.ANTIALIAS)
	
		image_data = (large_target_image.convert('RGB'), small_target_image.convert('RGB'))

		print 'Main image processed.'

		return image_data

		
class tileFitter:
	def __init__(self, small_tiles):
		self.smalltiles = small_tiles
	
	def __get_distance(self, sample_tile, small_tile, current_min):
		d = 0
		for i in range(len(sample_tile)):
			d += (sample_tile[i][0] - small_tile[i][0])**2 + (sample_tile[i][1] - small_tile[i][1])**2 + (sample_tile[i][2] - small_tile[i][2])**2
			
			if d > current_min:
				return d
				
		return d
		
	def get_best_fit_tile_idx(self, sample_tile):
		best_fit_tile_idx = None
		min_diff = sys.maxint
		tile_index = 0

		for small_tile in self.smalltiles:
			d = self.__get_distance(sample_tile, small_tile, min_diff)
			
			if d < min_diff:
				min_diff = d
				best_fit_tile_idx = tile_index

			tile_index = tile_index + 1

		return best_fit_tile_idx

		
class MosaicImage:
	def __init__(self, original_img):
		self.image = Image.new(original_img.mode, original_img.size)
		self.x_tile_count = self.image.size[0] / TILE_SIZE
		self.y_tile_count = self.image.size[1] / TILE_SIZE
		self.total_tile_count = self.x_tile_count * self.y_tile_count
		
	def patch_tile(self, tile_data, coords):
		img = Image.new('RGB', [TILE_SIZE, TILE_SIZE])
		img.putdata(tile_data)
		self.image.paste(img, coords)
		
	def save_mosaic(self, path):
		self.image.save(path)
		
				
class ProgressCounter:
	def __init__(self, total):
		self.total = total
		self.counter = 0

	def update(self):
		self.counter += 1
		sys.stdout.write("Progress: %s%% %s" % (100 * self.counter / self.total, "\r"))
    	sys.stdout.flush();
		

def fit_tiles(work_queue, result_queue, small_tiles):
	tf = tileFitter(small_tiles)
	
	while True:
		try:
			sample_tile, coords = work_queue.get(True)
			
			if sample_tile == QUEUE_EMPTY_VALUE:
				break
			
			fit_idx = tf.get_best_fit_tile_idx(sample_tile)
			result_queue.put((fit_idx, coords))
		except KeyboardInterrupt:
			pass
			
	result_queue.put((QUEUE_EMPTY_VALUE, QUEUE_EMPTY_VALUE))


def build_mosaic(result_queue, original_img, large_tiles):
	mosaic = MosaicImage(original_img)
	active_worker = WORKER_COUNT
	
	
	while True:
		try:
			fit_idx, coords = result_queue.get()
			
			if fit_idx == QUEUE_EMPTY_VALUE:
				active_worker -= 1
				
				if active_worker == 0:
					break
			else:
				tile_data = large_tiles[fit_idx]
				mosaic.patch_tile(tile_data, coords)	
		except KeyboardInterrupt:
			pass
		
	mosaic.save_mosaic(OUT_FILE_NAME)
	
	print('\nThe all process is finished')
		
		
def compose(tiles, original_img):
	large_tiles, small_tiles = tiles
	original_img_large, original_img_small = original_img
	
	large_tiles_list_type = map(lambda tile : list(tile.getdata()), large_tiles)
	small_tiles_list_type = map(lambda tile : list(tile.getdata()), small_tiles)
	
	mosaic = MosaicImage(original_img_large)
	x_count = mosaic.x_tile_count
	y_count = mosaic.y_tile_count
	
	work_queue = Queue(WORKER_COUNT)
	result_queue = Queue()

	try:
		Process(target=build_mosaic, args=(result_queue, original_img_large, large_tiles_list_type)).start()
		
		for i in range(WORKER_COUNT):
			Process(target=fit_tiles, args=(work_queue, result_queue, small_tiles_list_type)).start()
			
		progress = ProgressCounter(mosaic.x_tile_count * mosaic.y_tile_count)
		
		#%sample_tile, coords = work_queue.get(true)
		
		
		for x in range(x_count):
			for y in range(y_count):
				large_box = [x*TILE_SIZE, y*TILE_SIZE, (x+1)*TILE_SIZE, (y+1)*TILE_SIZE]
				small_box = [x*TILE_SIZE/TILE_BLOCK_SIZE, y*TILE_SIZE/TILE_BLOCK_SIZE, (x+1)*TILE_SIZE/TILE_BLOCK_SIZE, (y+1)*TILE_SIZE/TILE_BLOCK_SIZE]
				
				sample_tile = list(original_img_small.crop(small_box).getdata())
				work_queue.put((sample_tile, large_box))
				progress.update()

		
	except KeyboardInterrupt:
		print '\nHalting, saving partial image please wait...'	
		
	finally:	
		for i in range(WORKER_COUNT):
			work_queue.put((QUEUE_EMPTY_VALUE, QUEUE_EMPTY_VALUE))
	
	
	
def mosaic(original_imag_name, pic_files_path):
	TP = TileProcessor(pic_files_path)
	TIP = TargetImageProcessor(original_imag_name)
	
	tiles = TP.get_tiles()
	original_img = TIP.get_processed_targetimage()
	
	start_time = time()

	compose(tiles, original_img)
	
	end_time = time()

	print 'Total time cost : %d seconds' % (end_time - start_time)
		
if __name__ == '__main__':
	if len(sys.argv) < 3:
		print 'Usage: %s <image> <tiles directory>\r' % (sys.argv[0],)
	else:
		mosaic(sys.argv[1], sys.argv[2])
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		