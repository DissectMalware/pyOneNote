# pyOneNote
pyOneNote is a lightweight python library to read OneNote files. The main goal of this parser is to allow cybersecurity analyst to extract useful information from OneNote files.

# Installing the parser

Installing the latest development

```
pip install -U https://github.com/DissectMalware/pyOneNote/archive/master.zip --force
```
# Running the parser

To dump all embedded file in current directory
```
pyOneNote -f example.one 
```

To dump all embedded file in example.one into output_dir
```
pyOneNote -f example.one -o output_dir 
```
To dump all embedded file in example.one into output_dir and add .bin to the end of each filename
```
pyOneNote -f example.one -o output_dir -e bin
```

# Command Line
```
usage: main.py [-h] -f FILE [-o OUTPUT_DIR] [-e EXTENSION]
```

Note: pyOneNote is under active development

# How to Contribute
If you found a bug or would like to suggest an improvement, please create a new issue on the [issues page](https://github.com/DissectMalware/pyOneNote/issues).

Feel free to contribute to the project forking the project and submitting a pull request.

You can reach [me (@DissectMlaware) on Twitter](https://twitter.com/DissectMalware) via a direct message.
