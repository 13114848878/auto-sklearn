import numpy as np
cimport numpy as np

import scipy.sparse


from libc.stdio cimport *


'''	read_sparse_file (filename, num_features, num_points)

	Reads the data from a file containing sparse data into a scipy.sparse.csr_matrix (type float32).
	
	The number of features and the number of points have to be known ahead of time.
	Each pair is "index:value" and the row in the file equals the row in the matrix.
	The labels are assumed to be in a different file, in contrast to the SVMlight file format where the "target value" would be the first entry	in each line!
	The optional argument initial_length should estimate the number of elements	expected in the data set. If it is to small all arrays will be dynamically enlarged in steps of initial_length. If chosen to small, unnecessary reallocations slow things down. If to big, memory might be wasted while	loading the data.
	The optional argument offset should be -1 if the indices in the file start at 1! This is the case for the automl challenge, hence the default value.
	So far, only ascii #32 (space) is recognized as a whitespace. If the entries are tab-separated (or any other chararcter), this could easily be implemented here.
	
'''
def read_sparse_file(char *filename, int num_points,int num_features, int initial_length = 10000, int offset = -1):

	#cdef np.ndarray[float, ndim=1] 
	data = np.zeros(initial_length,dtype=np.float32)
	#cdef np.ndarray[int, ndim=1]
	indices = np.zeros(initial_length, dtype=np.int32)
	#cdef np.ndarray[int, ndim=1] 
	indptr = np.zeros(num_points+1, dtype=np.int32)
	
	# we have to dynamically enlarge the arrays, so we need to keep track of how many entries we already have
	cdef int num_entries = 0
	
	
	# variables for I/O
	cdef char* fname
	cdef FILE* cfile
	cdef ssize_t read
	cdef char whitespace

	#variables for the indices and values
	cdef int i=0,j
	cdef float v


	filename_byte_string = filename.encode("UTF-8")
	fname = filename_byte_string
	cfile = fopen(fname, "r")
		
	while True:
		# read the column and the value and store it
		read =fscanf(cfile, "%i:%f",&j,&v)
		# stop at EOF
		if (read == -1): break

		data[num_entries] = v;
		indices[num_entries] = j+offset
		num_entries += 1
		
		#enlarge the array if necessary
		if (num_entries == data.shape[0]):
			data.resize(data.shape[0]+initial_length)
			indices.resize(data.shape[0])
		
		# check if we hit a endline next to recognize the next row
		# It is cumbersome, but a way to reliably do it!
		whitespace = fgetc(cfile)
		while (whitespace==32):
			whitespace = fgetc(cfile)
		
		if (whitespace == '\n'):
			i+=1
			# stop if num_points have been read
			if (i >=num_points): break
			indptr[i] = num_entries
		else:
			ungetc(whitespace, cfile)

	fclose(cfile)
	
	
	#cut arrays to size
	data.resize(num_entries)
	indices.resize(num_entries)
	
	# fix the end of indptr
	for j in range (i,num_points+1):
		indptr[j] = num_entries
	return(scipy.sparse.csr_matrix((data,indices,indptr),shape=[num_points, num_features]))



'''
	see read_sparse_file, only difference: the value of every index present is 1, so there are no index:value pairs, but just indices.
	
'''
def read_sparse_binary_file(char *filename, int num_points, int num_features, int initial_length = 10000, int offset = -1):

	data = np.zeros(initial_length,dtype=np.bool)
	indices = np.zeros(initial_length, dtype=np.int32)
	cdef np.ndarray[int, ndim=1] indptr = np.zeros(num_points+1, dtype=np.int32)
	
	# we have to dynamically enlarge the arrays, so we need to keep track of how many entries we already have
	cdef int num_entries = 0
	
	# variables for I/O
	cdef char* fname
	cdef FILE* cfile
	cdef ssize_t read
	cdef char whitespace

	#variables for the indices and values
	cdef int i=0,j

	filename_byte_string = filename.encode("UTF-8")
	fname = filename_byte_string
	cfile = fopen(fname, "r")
		
	while True:
		# read the column and the value and store it
		read =fscanf(cfile, "%f",&j)
		# stop at EOF
		if (read == -1): break

		data[num_entries] = True;
		indices[num_entries] = j+offset
		num_entries += 1
		
		#enlarge the array if necessary
		if (num_entries == data.shape[0]):
			data.resize(data.shape[0]+initial_length)
			indices.resize(data.shape[0])
		
		# check if we hit a endline next to recognize the next row
		# It is cumbersome, but a way to reliably do it!
		whitespace = fgetc(cfile)
		while (whitespace==32):
			whitespace = fgetc(cfile)
		
		if (whitespace == '\n'):
			i+=1
			# stop if num_points have been read
			if (i >=num_points): break
			indptr[i] = num_entries
		else:
			ungetc(whitespace, cfile)

	fclose(cfile)
	
	
	#cut arrays to size
	data.resize(num_entries)
	indices.resize(num_entries)
	
	# fix the end of indptr
	for j in range (i,num_points+1):
		indptr[j] = num_entries
	
	return(scipy.sparse.csr_matrix((data,indices,indptr),shape=[num_points, num_features], dtype=np.bool))


'''	read_dense_file (filename, num_features, num_points)

	Reads the data from a file containing dense data into a numpy array (type float32)
	
	The number of features and the number of points have to be known ahead of time.
	
	The function does not check for EOF or missing values, so be cautious!
'''
def read_dense_file(filename, num_points, num_features):

	cdef np.ndarray[float, ndim=2] data = np.zeros([num_points, num_features],dtype=np.float32)
	
	# variables for I/O
	cdef char* fname
	cdef FILE* cfile

	#variable for the indices and values
	cdef int i=0,j=0
	cdef float v

	filename_byte_string = filename.encode("UTF-8")
	fname = filename_byte_string
	cfile = fopen(fname, "r")
		
	for i in range(num_points):
		for j in range(num_features):
			fscanf(cfile, "%f",&v)
			data[i,j] = v
	fclose(cfile)

	# if only one predictor is present, convert it into a 1D array
	if data.shape[1] == 1:
		return(data.flatten())
	
	return(data)



def read_dense_file_unknown_width(filename, num_points):
	# variables for I/O
	cdef char* fname
	cdef FILE* cfile
	cdef int rc;

	#variables for the indices and values
	cdef int num_cols=0

	filename_byte_string = filename.encode("UTF-8")
	fname = filename_byte_string
	cfile = fopen(fname, "r")

	#count the number of columns in the first line
	rc = fgetc(cfile)
	while True:
		# read a column
		while (rc != ' ') and (rc != '\n'):
			rc=fgetc(cfile)
		
		while (rc == ' '):
			rc=fgetc(cfile)
		num_cols+=1
		
		if (rc == '\n'): break
	fclose(cfile)
	return(read_dense_file(filename, num_points,num_cols))


# function copied from the reference implementation
# no need to really optimize them because they don't take long

def read_first_line (filename):
	'''Read fist line of file'''
	data =[]
	with open(filename, "r") as data_file:
		line = data_file.readline()
		data = line.strip().split()
	return data  


def file_to_array (filename, verbose=False):
	''' Converts a file to a list of list of STRING
	It differs from np.genfromtxt in that the number of columns doesn't need to be constant'''
	data =[]
	with open(filename, "r") as data_file:
		if verbose: print ("Reading {}...".format(filename))
		lines = data_file.readlines()
		if verbose: print ("Converting {} to correct array...".format(filename))
		data = [lines[i].strip().split() for i in range (len(lines))]
	return data


def predict_RAM_usage(X, categorical, size_in_byte=4):
	"""Return estimated RAM usage of dataset after OneHotEncoding in bytes."""
	estimated_columns = 0
	for i, cat in enumerate(categorical):
		if cat:
			unique_values = np.unique(X[:, i])
			num_unique_values = np.sum(np.isfinite(unique_values))
			estimated_columns += num_unique_values
		else:
			estimated_columns += 1
	estimated_ram = estimated_columns * X.shape[0] * size_in_byte
	return estimated_ram

