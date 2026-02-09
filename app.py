import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image
import io
import zipfile

# Page Config
st.set_page_config(layout="wide", page_title="Batch Image Cropper")

# Custom CSS for better layout
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

st.title("✂️ Interactive Batch Image Cropper")
st.markdown("""
**Instructions:**
1. Upload your batch of images.
2. Adjust settings (Rotation & Aspect Ratio) in the sidebar.
3. Draw your crop box on the **Reference Image**.
4. Click **"Crop All & Download"** to process the entire batch.
""")

# --- 1. File Upload ---
uploaded_files = st.file_uploader(
    "Upload Images (PNG, JPG, JPEG)", 
    type=['png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

if uploaded_files:
    # --- 2. Sidebar Controls ---
    st.sidebar.header("⚙️ Settings")

    # A. Select Reference Image
    # We use this image to define the crop box for the whole batch
    img_map = {f.name: f for f in uploaded_files}
    ref_img_name = st.sidebar.selectbox(
        "Select Reference Image (for preview)", 
        list(img_map.keys()),
        index=0
    )
    ref_file = img_map[ref_img_name]
    
    # Load the image
    raw_image = Image.open(ref_file)

    # B. Rotation Tool
    st.sidebar.subheader("Rotation")
    rotate_angle = st.sidebar.slider("Rotate (Degrees)", -180, 180, 0, 1)
    
    # Apply rotation to the preview immediately
    if rotate_angle != 0:
        # expand=True ensures we don't cut off corners when rotating
        processed_image = raw_image.rotate(-rotate_angle, expand=True)
    else:
        processed_image = raw_image

    # C. Aspect Ratio Lock
    st.sidebar.subheader("Crop Box Ratio")
    aspect_choice = st.sidebar.radio(
        "Lock Aspect Ratio", 
        ["Free", "1:1 (Square)", "16:9", "4:3"]
    )
    
    aspect_ratio = None
    if aspect_choice == "1:1 (Square)":
        aspect_ratio = (1, 1)
    elif aspect_choice == "16:9":
        aspect_ratio = (16, 9)
    elif aspect_choice == "4:3":
        aspect_ratio = (4, 3)

    # --- 3. Interactive Cropper ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Draw Crop Box")
        # st_cropper returns the box coordinates when return_type='box'
        # realtime_update=True makes the UI feel snappier
        crop_box = st_cropper(
            processed_image,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=aspect_ratio,
            return_type='box'
        )

    with col2:
        st.subheader("Preview Result")
        # Calculate coordinates from the box dict
        rect = (
            crop_box['left'], 
            crop_box['top'], 
            crop_box['left'] + crop_box['width'], 
            crop_box['top'] + crop_box['height']
        )
        
        # Show what the final single image looks like
        preview_crop = processed_image.crop(rect)
        st.image(preview_crop, caption=f"Result: {preview_crop.size}", use_container_width=True)

    # --- 4. Batch Processing Logic ---
    st.divider()
    
    # We store the processing trigger in a button
    if st.button(f"🚀 Crop All {len(uploaded_files)} Images & Prepare Download"):
        
        # Buffer for the zip file
        zip_buffer = io.BytesIO()
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for i, file in enumerate(uploaded_files):
                    status_text.text(f"Processing {file.name}...")
                    
                    # 1. Open
                    img = Image.open(file)
                    
                    # 2. Rotate (Apply same rotation as reference)
                    if rotate_angle != 0:
                        img = img.rotate(-rotate_angle, expand=True)
                    
                    # 3. Crop (Apply same coordinates as reference)
                    # Note: This assumes all images are same size/dimensions.
                    cropped_img = img.crop(rect)
                    
                    # 4. Save to memory buffer
                    img_byte_arr = io.BytesIO()
                    
                    # Detect format (default to PNG if unknown)
                    fmt = file.type.split('/')[-1].upper() if file.type else 'PNG'
                    if fmt == 'JPG': fmt = 'JPEG'
                    
                    cropped_img.save(img_byte_arr, format=fmt)
                    
                    # 5. Write to Zip
                    zf.writestr(f"cropped_{file.name}", img_byte_arr.getvalue())
                    
                    # Update progress
                    progress_bar.progress((i + 1) / len(uploaded_files))
            
            status_text.success("Processing Complete!")
            
            # Show Download Button
            st.download_button(
                label="⬇️ Download Cropped Images (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="batch_cropped_images.zip",
                mime="application/zip"
            )
            
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.warning("Note: Batch cropping works best when all uploaded images have the same dimensions.")

else:
    # Empty state
    st.info("👆 Please upload images in the sidebar or top section to begin.")
