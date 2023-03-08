import imageio

input_file = 'front_wide.h264'
output_prefix = 'output'

reader = imageio.get_reader(input_file)
for i, frame in enumerate(reader):
    imageio.imwrite(f'{output_prefix}_{i:04d}.png', frame)

