import datalab

# Save a version first to pin your configuration
result = datalab.run_pipeline(
    pipeline_id="pl_WMV8zsDCSS0z",
    filepath="document.pdf",
)

print(result)