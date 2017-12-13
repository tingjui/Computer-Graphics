import numpy as np
from PIL import Image

data = np.load('data.npy')
data2 = None

for i in range(len(data)):
	pic = np.reshape(data[i],[306,408,-1])	
	im = Image.fromarray(np.uint8(pic))
	
	im = im.resize((int(im.size[0]/2.), int(im.size[1]/2.)), Image.ANTIALIAS)
	
	#im.save('all_pics\pic' + str(i) + '.jpg')
	
	im = np.array(im)
	im = np.reshape(im, -1)

	im = np.expand_dims(im, axis=0)
	if data2 is None:
		data2 = im
	else:
		data2 = np.concatenate((data2, im), axis=0)

		
np.save('data2.npy', data2)




