import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image
import io
import zipfile

# Page Config
st.set_page_config(layout="wide", page_title="Batch Image Cropper")

# --- Session State Initialization ---
# We use this to track the coordinates so we can update them
# via both the slider/mouse AND the manual text inputs.
if 'crop_coords' not in st.session_state:
    st.session_state.crop_coords = None 

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
    # Map filenames to file objects
    img_map = {f.name: f for f in uploaded_files}

    # --- 2. Sidebar Settings ---
    st.sidebar.header("⚙️ Settings")

    # A. Select Reference Image
    ref_img_name = st.sidebar.selectbox(
        "Select Reference Image", 
        list(img_map.keys()),
        index=0
    )
    ref_file = img_map[ref_img_name]
    raw_image = Image.open(ref_file)
    
    # B. Rotation
    rotate_angle = st.sidebar.slider("Rotate (Degrees)", -180, 180, 0, 1)
    if rotate_angle != 0:
        processed_image = raw_image.rotate(-rotate_angle, expand=True)
    else:
        processed_image = raw_image

    img_w, img_h = processed_image.size

    # --- 3. Manual Coordinate Inputs (The new feature) ---
    st.sidebar.divider()
    st.sidebar.subheader("📍 Manual Coordinates")
    st.sidebar.info(f"Image Size: {img_w} x {img_h} px")

    # We use a form so the app doesn't reload on every single keystroke
    with st.sidebar.form("manual_coords_form"):
        col_manual_1, col_manual_2 = st.columns(2)
        with col_manual_1:
            man_left = st.number_input("Left (x)", min_value=0, max_value=img_w, value=0)
            man_top = st.number_input("Top (y)", min_value=0, max_value=img_h, value=0)
        with col_manual_2:
            man_right = st.number_input("Right", min_value=0, max_value=img_w, value=min(200, img_w))
            man_bottom = st.number_input("Bottom", min_value=0, max_value=img_h, value=min(200, img_h))
        
        apply_manual = st.form_submit_button("Apply Manual Coords")

    # Logic: If user clicked "Apply", calculate the box (left, top, width, height)
    # and save to session state to force the cropper to update.
    initial_box = None
    if apply_manual:
        width = man_right - man_left
        height = man_bottom - man_top
        if width > 0 and height > 0:
            # (left, top, width, height) is the format st_cropper expects for 'box'
            st.session_state.crop_coords = (man_left, man_top, width, height)
            # We create a unique key to force the widget to re-render with new box
            if 'cropper_key' not in st.session_state: st.session_state.cropper_key = 0
            st.session_state.cropper_key += 1
        else:
            st.sidebar.error("Invalid coordinates (Right must be > Left, Bottom > Top)")

    # --- 4. Interactive Cropper ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Draw Crop Box")
        
        # Use a dynamic key so we can reset the box programmatically
        c_key = f"cropper_{st.session_state.get('cropper_key', 0)}"

        # If we have manual coords in state, pass them to 'box'
        box_args = {}
        if st.session_state.crop_coords:
            box_args['box'] = st.session_state.crop_coords

        crop_box = st_cropper(
            processed_image,
            realtime_update=True,
            box_color='#FF0000',
            return_type='box',
            key=c_key,
            **box_args
        )

    with col2:
        st.subheader("Preview & Coords")
        
        # Calculate standard PIL coordinates (Left, Top, Right, Bottom)
        # crop_box returns: left, top, width, height
        rect_left = crop_box['left']
        rect_top = crop_box['top']
        rect_right = crop_box['left'] + crop_box['width']
        rect_bottom = crop_box['top'] + crop_box['height']
        
        rect = (rect_left, rect_top, rect_right, rect_bottom)
        
        # Display the coordinates prominently so user can copy them
        st.code(f"""
Left:   {rect_left}
Top:    {rect_top}
Right:  {rect_right}
Bottom: {rect_bottom}
        """, language="yaml")
        
        # Show Preview
        preview_crop = processed_image.crop(rect)
        st.image(preview_crop, caption=f"Size: {preview_crop.size}", use_container_width=True)

    # --- 5. Batch Processing ---
    st.divider()
    
    if st.button(f"🚀 Crop All {len(uploaded_files)} Images"):
        zip_buffer = io.BytesIO()
        progress_bar = st.progress(0)
        
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for i, file in enumerate(uploaded_files):
                try:
                    img = Image.open(file)
                    # Apply Rotation
                    if rotate_angle != 0:
                        img = img.rotate(-rotate_angle, expand=True)
                    
                    # Apply Crop
                    cropped_img = img.crop(rect)
                    
                    # Save
                    img_byte_arr = io.BytesIO()
                    fmt = file.type.split('/')[-1].upper() if file.type else 'PNG'
                    if fmt == 'JPG': fmt = 'JPEG'
                    cropped_img.save(img_byte_arr, format=fmt)
                    
                    zf.writestr(f"cropped_{file.name}", img_byte_arr.getvalue())
                except Exception as e:
                    print(f"Error processing {file.name}: {e}")
                
                progress_bar.progress((i + 1) / len(uploaded_files))
        
        st.success("Done!")
        st.download_button(
            label="⬇️ Download ZIP",
            data=zip_buffer.getvalue(),
            file_name="batch_cropped.zip",
            mime="application/zip"
        )

else:
    st.info("👆 Please upload images to begin.")
