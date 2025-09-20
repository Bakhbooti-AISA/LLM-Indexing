import sys

def redirect_output_to_file(filename, func, *args, **kwargs):
	original_stdout = sys.stdout
	try:
		with open(filename, 'w') as f:
			sys.stdout = f
			func(*args, **kwargs)
	finally:
		sys.stdout = original_stdout

# Example usage:
def filename_gen():
	for i in range(1,44,1):
		print("datasets/transactional_gpt-5/transactional_hars_gpt-5/network-logs-prompt-"+str(i)+".har")

redirect_output_to_file("src/cur_har_run.txt", filename_gen)
print("This line goes to the console.")