"""
Log Converter Script v1.3.0

Converts downloaded logs from a single file into how they are representated on Learn
"""
#!/usr/bin/python3

import argparse
import json
import gzip
import os
import sys
from datetime import datetime

def get_version():
    """
    Gets the version of the convertlogs script.
    Make sure to increment the version appropriately when making changes.
    """
    return "1.3.0"

def get_args(args):
    """ Returns the command-line args parsed into an object """
    version = 'Version: {}'.format(get_version())
    parser = argparse.ArgumentParser(description=version)
    parser.add_argument("-f", "--file_path", required=True)
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("-t", "--output_type")
    return parser.parse_args(args)

def check_preconditions(input_path, output):
    """
    Validates the user-specified input and output.
    Returns a string representing the errors.
    Returns an empty string if no errors were found.
    """
    error_messages = []
    if not os.path.exists(input_path):
        error_messages.append('The file or directory "{}" does not exist.'.format(input_path))
    if not (os.path.exists(output) and os.listdir(output) == []):
        error_messages.append('The output directory "{}" must exist and be empty.'.format(output))
    return '\n'.join(error_messages)

def to_list(path):
    """ Takes a path to a file or directory and returns a list of files to convert """
    if os.path.isfile(path):
        return [path]

    file_paths = []
    for root, _, files in os.walk(path):
        file_paths.extend([os.path.join(root, filename) for filename in files])

    return file_paths

def decompress_logs(file_paths):
    """
    Decompresses all the logs found in the path.
    Deletes the original .gz files.
    """
    all_paths = set(file_paths)
    compressed_files = set(path for path in all_paths if path.endswith('.gz'))
    decompressed_files = all_paths.difference(compressed_files)

    for compressed in compressed_files:
        with gzip.open(compressed, 'rb') as comp:
            decompressed = compressed.rstrip('.gz')
            with open(decompressed, 'wb') as decomp:
                decomp.write(comp.read())
                decompressed_files.add(decompressed)

    for comp in compressed_files:
        os.remove(comp)

    return list(decompressed_files)

def extract_date(file_path):
    """ Determines the date the log represents by examing the path """
    filename = os.path.basename(file_path)
    parts = filename.split('.')
    if len(parts) < 6:
        return False

    datestr = '.'.join(parts[:4])
    format_str = '%Y.%m.%d.%H'

    return datetime.strptime(datestr, format_str)

class FileWriter():
    """Encapsulates file I/O for performance tuning"""
    def __init__(self, output_directory, output_type=None):
        self.open_files = None
        self.output_directory = output_directory

        if output_type == 'json':
            self.helper = JsonFileHelper(output_directory)
        else:
            self.helper = FlatFileHelper(output_directory)

    def __enter__(self):
        self.prepare()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.complete()

    def prepare(self):
        """Enable the object to write files"""
        self.open_files = dict()

    def complete(self):
        """Performs a batch close on all open files"""
        for filename in self.open_files:
            self.open_files[filename].close()
        self.open_files = None

    def write_to_file(self, data):
        """Writes the json object to the appropriate file."""
        if self.open_files is None:
            raise Exception('Must call "prepare" first.')

        filename = self.helper.get_filename(data)
        learn_log = self.__get_open_file(filename)
        self.helper.write(learn_log, data)

    def __get_open_file(self, filename):
        """Makes sure the file exists and is open"""
        if filename not in self.open_files:
            directory = os.path.dirname(filename)
            if not os.path.exists(directory):
                os.makedirs(directory)
            self.open_files[filename] = open(filename, 'w')

        return self.open_files[filename]

class FlatFileHelper():
    """Helper when output type is just a normal file"""
    def __init__(self, output_directory):
        self.output_directory = output_directory

    @staticmethod
    def write(open_file, data):
        """Write the json object to the file"""
        open_file.write(data['message'] + '\n')

    def get_filename(self, data):
        """Determines the filename to use when writing the data to file"""
        old_path = '/usr/local/blackboard'
        new_path = os.path.join(self.output_directory, data['host'])
        if data['path'].startswith(old_path):
            filename = data['path'].replace(old_path, new_path)
        else:
            filename = new_path + data['path']
        return filename

class JsonFileHelper():
    """Helper when output type is a single json file"""
    def __init__(self, output_directory):
        self.output_directory = output_directory

    @staticmethod
    def write(open_file, data):
        """Writes the json object to the appropriate file."""
        json.dump(data, open_file)
        open_file.write("\n")

    def get_filename(self, data):
        """Determines the filename to use when writing the data to file"""
        new_path = os.path.join(self.output_directory, data['host'])
        return new_path + "/logs.json"

def convert_file(file_path, writer):
    """
    Coverts a flat file into the Learn representation.
    Logs are written to output_directory.
    """
    print('Converting "{}" to "{}"'.format(file_path, writer.output_directory))
    total_line = ""
    with open(file_path, errors='ignore') as log:
        for line in log:
            total_line += line
            if line.endswith("}\n"):
                try:
                    data = json.loads(total_line.replace("\n", ""))
                    writer.write_to_file(data)
                    total_line = ""
                except: # pylint: disable=W0702
                    # Fail silently and try to grab the next line.
                    continue

def convert(file_paths, output_directory, output_type=None):
    """ Converts a list of logs to the "Learn" format. """
    newpaths = []
    for path in file_paths:
        if extract_date(path):
            newpaths.append(path)

    newpaths.sort(key=extract_date)

    with FileWriter(output_directory, output_type) as writer:
        for path in newpaths:
            convert_file(path, writer)

def decompress_and_convert(file_path, output_directory, output_type=None):
    """
    Takes the path to the log or directory of logs to be converted
    and decompresses and coverts them.
    """
    logs = to_list(file_path)
    ready_to_covert = decompress_logs(logs)
    convert(ready_to_covert, output_directory, output_type)

def main():
    """ Main """
    args = get_args(sys.argv[1:])
    file_path = args.file_path
    output_folder = args.output
    output_type = args.output_type

    error_messages = check_preconditions(file_path, output_folder)

    if not error_messages:
        decompress_and_convert(file_path, output_folder, output_type)
    else:
        print(error_messages)

if __name__ == '__main__':
    main()