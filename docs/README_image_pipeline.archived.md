# AI Image Generation Pipeline

This project contains an automated pipeline for generating images using AI models. The workflow involves two stages:
1. Expanding a simple user prompt into a detailed image description using Qwen 3 model
2. Generating an actual image from that detailed description using Stable Diffusion WebUI/Forge

## Requirements

- Python 3.x with `requests` library installed (`pip install requests`)
- Running Qwen model on EC2 instance (port 11435)  
- Stable Diffusion WebUI/Forge running on EC2 instance (port 7860)

## Setup

1. Install dependencies:
   ```
   pip install requests
   ```

2. Configure the script with your EC2 settings in `image_pipeline.py`:
   - `EC2_IP`: Your EC2 instance IP address
   - `QWEN_API_PORT`: Port for Qwen API (default: 11435)
   - `IMAGE_API_PORT`: Port for Stable Diffusion API (default: 7860)

## Usage

Run the pipeline:
```
python image_pipeline.py
```

The script will:
1. Prompt you for a simple image idea
2. Expand that idea using Qwen into a detailed prompt 
3. Generate an image with Stable Diffusion
4. Save both the generated prompt and image to files

## Model Information

Currently configured to use only `qwen3-coder:latest` model as requested. This model is optimized for prompt engineering tasks and works well with Flux and Z-Image models.

## Troubleshooting

If you encounter errors:
- Ensure your EC2 instance is running and the SSH tunnel is active
- Verify that both Qwen API and Stable Diffusion APIs are accessible 
- Check that models are loaded on the EC2 instance with `.\qwen_model.ps1 list`