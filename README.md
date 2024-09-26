# hbcd-loris2reproschema

This repository provides a converter tool to transform data from the HBCD LORIS format to the ReproSchema format.

This repo was generated using [`to_reproschema`](https://github.com/yibeichan/reproschema-py/blob/converter/reproschema/to_reproschema.py)

> Note: The converter is still a work in progress (WIP). Once complete, it will allow seamless conversion between formats using the steps outlined below.

## Usage

Once the converter is ready, you can use the following command to perform the conversion:

```bash
python -m reproschema.to_reproschema <csv_file> <yaml_file> <output_path>

```

- `<csv_file>`: Path to the input CSV file in the HBCD LORIS format.
- `<yaml_file>`: Path to the YAML configuration file for ReproSchema.
- `<output_path>`: Directory where the output files will be saved.

## Versioning and Tagging Workflow

```
# Check the status of your repository
git status           

# Stage the changes
git add .

# Commit the changes with a descriptive message
git commit -m "Implement feature X"

# Tag the release with version number (e.g., v1.0.0)
git tag -a vX.Y.Z -m "Convert HBCD-LORIS vX.Y.Z"

# Push the changes to the main branch
git push origin main  

# Push the tag to the remote repository
git push origin vX.Y.Z
```

### Example

If you made changes and are ready to release version 1.0.0, the commands would look like this:

```
git add .
git commit -m "Implement conversion for HBCD-LORIS to ReproSchema"
git tag -a v1.0.0 -m "Convert HBCD-LORIS to ReproSchema v1.0.0"
git push origin main  
git push origin v1.0.0
```