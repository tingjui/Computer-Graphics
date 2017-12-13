import numpy as np
from PIL import Image


data = np.load('data2.npy')
k = 4
sample_idx = np.arange(len(data))
np.random.shuffle(sample_idx)

cluster_mean = np.zeros([k, len(data[0])])

for i in range(k):
	cluster_mean[i] = data[sample_idx[i]].copy()
	

for i in range(30):
	
	cluster_mean_updater = np.zeros([k, len(data[0])])
	num_each_cluster = np.zeros(k)
	
	for j in range(len(data)):
		distance = np.linalg.norm((data[j]-cluster_mean[0]))
		class_idx = 0
		
		for m in range(1,k):
			if np.linalg.norm(data[j]-cluster_mean[m]) < distance:
				distance = np.linalg.norm(data[j]-cluster_mean[m])
				class_idx = m
				
		
		cluster_mean_updater[class_idx] += data[j]
		num_each_cluster[class_idx] += 1

	for j in range(k):
		cluster_mean[j] = cluster_mean_updater[j] / num_each_cluster[j]
		
for i in range(k):
	distance = np.linalg.norm(cluster_mean[i]-data[0])
	pic_idx = 0
	
	for j in range(1, len(data)):
		if np.linalg.norm(cluster_mean[i] - data[j]) < distance:
			distance = np.linalg.norm(cluster_mean[i] - data[j])
			pic_idx = j

	cluster_mean[i] = data[pic_idx]		
			




for i in range(k):		
	#pic = np.reshape(cluster_mean[i],[306,408,-1])		
	pic = np.reshape(cluster_mean[i], [153, 204, -1])
	im = Image.fromarray(np.uint8(pic))
	im.show()
	#im.save('cluster_mean' + str(i) + '.jpg')








