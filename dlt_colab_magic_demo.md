# [Demo]: Google Colab Notebook 🚀

This notebook demonstrates how to manage and deploy data pipelines using the DLT (Data Loading Tool) CLI, directly within an IPython notebook via magic commands. We’ll recreate the pipeline setup from [Colab Demo](https://colab.research.google.com/drive/1NfSB1DpwbbHX9_t5vlalBTf13utwpMGx?usp=sharing#scrollTo=GYREioraz1m6), using %pipeline, %init, %schema, and other magic commands.

### **What you'll learn:**
1. How to list, sync, and manage pipelines using `%pipeline`.
2. How to initialize a new DLT pipeline with `%init`.
3. How to manage schemas using `%schema`.
4. How to check DLT version with `%dlt_version`.

Let's dive in!

# 1. **Setup Environment**
First, you need to install the required DLT tool if it's not already installed.


```python
# Install the dlt package
!pip install dlt
```

# 2. **Initialize a Pipeline**
You can initialize a new DLT pipeline by specifying the source and destination. This will generate the necessary scripts for data loading.

### Initialize a New Pipeline
In this example, we’ll initialize a pipeline from a `pokemon` source to a `duckdb` destination.



```python
# Initialize a pipeline with a source and destination
%init --source_name pokemon --destination_name duckdb
```

# 3. **Sync a Pipeline**
After initializing a pipeline, you can run a sync operation to load data from the source to the destination.
### Sync the Pipeline
Use the `sync` operation to load data.



```python
%pipeline --operation sync --pipeline_name pokemon_duckdb
```

# 4. **Manage Pipelines**
You can list all available pipelines using the %pipeline magic command with the list-pipelines operation.

### **List Available Pipelines**
You can see all available pipelines by running the following command:


```python
# Magic command to list pipelines
%pipeline --operation list-pipelines
```

### **Pipeline Information**
To get detailed information on a specific pipeline, use the info operation, specifying the pipeline name.




```python
%pipeline --operation info --pipeline_name pokemon
```

# 5. **Managing Schemas**
You can inspect, convert, or upgrade the schema used in the pipeline by specifying a schema file path.
### Manage Schema
To show the schema in JSON format:



```python
# Replace <schema_file_path> with the actual schema file path
%schema --file_path <schema_file_path> --format json
```

# 6. **Check DLT Version**
It's always good practice to check the version of the DLT tool in use.
### Check DLT Version
Ensure that you’re using the latest version of DLT.



```python
# Check DLT version
%dlt_version
```

# 7. **Enable/Disable Telemetry**
Control telemetry settings for your DLT operations.
### Manage Telemetry
You can enable or disable telemetry globally.



```python
# Enable telemetry
%settings --enable-telemetry

# Disable telemetry
%settings --disable-telemetry
```

# 8. **Additional Operations**
You can explore other DLT pipeline operations like trace, failed-jobs, and drop-pending-packages.
### Explore More Pipeline Operations
Check out these additional operations for pipeline management.



```python
# Trace pipeline execution
%pipeline --operation trace --pipeline_name pokemon

# Check for failed jobs
%pipeline --operation failed-jobs --pipeline_name pokemon

# Drop pending packages
%pipeline --operation drop-pending-packages --pipeline_name pokemon
```

## 🎉 **Finish!** *🎉*
By using the magic commands %pipeline, %init, %schema, and others, we've streamlined the DLT pipeline management process within a Colab notebook.
