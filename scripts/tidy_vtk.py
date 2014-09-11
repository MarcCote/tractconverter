#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import argparse

from itertools import islice


def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_vtk', type=str, help='VTK file to beautify.')
    parser.add_argument('output_vtk', type=str, help="Name of the beautified VTK file.")
    args = parser.parse_args()

    # Check for invalid arguments
    if not os.path.isfile(args.input_vtk):
        parser.error("Invalid file path. Specify path to a file.")

    if os.path.isfile(args.output_vtk):
        parser.error("Output file already exists, will not overwrite.")

    return args


def main():
    args = parse_arguments()

    lines = list(open(args.input_vtk))

    for i, l in enumerate(lines):
        if l.startswith('LINES'):
            break

    i += 1  # We need to format the line after section LINES.
    it = iter(lines[i].split())

    formatted_lines = []
    try:
        while True:
            nb_points = next(it)
            formatted_lines.append(" ".join([nb_points] + take(int(nb_points), it)) + "\n")
    except StopIteration:
        pass

    lines = lines[:i] + formatted_lines + lines[i+1:]

    open(args.output_vtk, 'w').write("".join(lines))

if __name__ == '__main__':
    main()
