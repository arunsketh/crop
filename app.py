import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image, ImageDraw
import io
import zipfile

# Page Config
st.set_page_config(layout="wide", page_title="Batch Image Cropper")

# Custom CSS
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

# --- 1. File Upload ---
uploaded_files = st.file_uploader(
    "Upload Images (PNG, JPG, JPEG)", 
    type=['png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

if uploaded_files:
    img_map = {f.name: f for f in uploaded_files}

    # --- 2. General Settings ---
    st.sidebar.header("⚙️ General Settings")
    
    # Reference Image
    ref_img_name = st.sidebar.selectbox(
        "Select Reference Image", 
        list(img_map.keys()),
        index=0
    )
    ref_file = img_map[ref_img_name]
    raw_image = Image.open(ref_file)
    
    # Rotation
    rotate_angle = st.sidebar.slider("Rotate (Degrees)", -180, 180, 0, 1)
    
    # Apply Rotation
    if rotate_angle != 0:
        processed_image = raw_image.rotate(-rotate_angle, expand=True)
    else:
        processed_image = raw_image

    img_w, img_h = processed_image.size

    # --- 3. Crop Method Selection ---
    st.sidebar.divider()
    st.sidebar.subheader("📍 Crop Method")
    
    # Toggle between Mouse Drawing and Manual Numbers
    crop_mode = st.sidebar.radio("Input Mode", ["Draw Box (Mouse)", "Manual Coordinates (Numbers)"])

    rect = None # This will store final (left, top, right, bottom)

    col1, col2 = st.columns([2, 1])

    # --- MODE A: DRAW (Standard) ---
    if crop_mode == "Draw Box (Mouse)":
        with col1:
            st.subheader("Draw Crop Box")
            # The standard library usage without the invalid 'box' argument
            crop_box = st_cropper(
                processed_image,
                realtime_update=True,
                box_color='#FF0000',
                return_type='box'
            )
            
            # Extract coordinates from the library's return value
            rect_left = crop_box['left']
            rect_top = crop_box['top']
            rect_right = crop_box['left'] + crop_box['width']
            rect_bottom = crop_box['top'] + crop_box['height']
            rect = (rect_left, rect_top, rect_right, rect_bottom)

    # --- MODE B: MANUAL (Custom Implementation) ---
    else:
        st.sidebar.info(f"Image Dimensions: {img_w}w x {img_h}h")
        
        # Manual Inputs
        with st.sidebar.form("manual_coords"):
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                m_left = st.number_input("Left", 0, img_w, 0)
                m_top = st.number_input("Top", 0, img_h, 0)
            with col_m2:
                m_right = st.number_input("Right", 0, img_w, min(200, img_w))
                m_bottom = st.number_input("Bottom", 0, img_h, min(200, img_h))
            
            st.form_submit_button("Update Preview")
            
        rect = (m_left, m_top, m_right, m_bottom)

        # Since st_cropper can't accept coords, we manually draw the box on the image
        # so the user can see what they are doing.
        with col1:
            st.subheader("Manual Preview")
            preview_with_box = processed_image.copy()
            draw = ImageDraw.Draw(preview_with_box)
            
            # Draw Rectangle (Red, 3px width)
            draw.rectangle(rect, outline="red", width=5)
            
            # Show the static image with the drawing
            st.image(preview_with_box, width="stretch")

    # --- 4. Result Preview (Common to both modes) ---
    with col2:
        st.subheader("Crop Result")
        
        # Validate coordinates
        if rect[2] > rect[0] and rect[3] > rect[1]:
            final_crop = processed_image.crop(rect)
            st.image(final_crop, caption=f"Size: {final_crop.size}", width="stretch")
            
            # Display coordinates for copying
            st.code(f"L: {rect[0]}\nT: {rect[1]}\nR: {rect[2]}\nB: {rect[3]}")
        else:
            st.warning("Invalid Coordinates! Right must be > Left and Bottom > Top.")

    # --- 5. Batch Processing ---
    st.divider()
    
    if st.button(f"🚀 Crop All {len(uploaded_files)} Images"):
        if rect[2] <= rect[0] or rect[3] <= rect[1]:
            st.error("Please select a valid crop area first.")
        else:
            zip_buffer = io.BytesIO()
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for i, file in enumerate(uploaded_files):
                    status_text.text(f"Processing {file.name}...")
                    try:
                        img = Image.open(file)
                        if rotate_angle != 0:
                            img = img.rotate(-rotate_angle, expand=True)
                        
                        cropped_img = img.crop(rect)
                        
                        img_byte_arr = io.BytesIO()
                        fmt = file.type.split('/')[-1].upper() if file.type else 'PNG'
                        if fmt == 'JPG': fmt = 'JPEG'
                        cropped_img.save(img_byte_arr, format=fmt)
                        
                        zf.writestr(f"cropped_{file.name}", img_byte_arr.getvalue())
                    except Exception as e:
                        print(f"Error: {e}")
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
            
            status_text.success("Processing Complete!")
            st.download_button(
                label="⬇️ Download ZIP",
                data=zip_buffer.getvalue(),
                file_name="batch_cropped.zip",
                mime="application/zip"
            )

else:
    st.info("👆 Please upload images to begin.")
