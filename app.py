import streamlit as st
import segno
import numpy as np
from PIL import Image
import io
from pyzbar.pyzbar import decode
import re
import uuid

st.set_page_config(page_title="QR Made Easy", layout="wide")

# Title
st.markdown("# QR :red[Made] Easy")
st.markdown("Welcome to QR Made Easy, the all-in-one platform to create, scan and customize QR codes effortlessly. Whether you're promoting a brand, sharing a link, vcard or email, our easy-to-use tools let you style your QR codes with colors and logos. Choose from multiple formats and bring creativity to every QR. Explore and enjoy this world of QR.")

# Function to create vCard string
def make_vcard_string(name, phone, email):
    vcard = ["BEGIN:VCARD", "VERSION:3.0", f"N:{name}", f"FN:{name}"]
    if phone:
        vcard.append(f"TEL;TYPE=CELL:{phone}")
    if email:
        vcard.append(f"EMAIL;TYPE=INTERNET:{email}")
    vcard.append("END:VCARD")
    return "\n".join(vcard)

# Function to validate inputs
def validate_inputs(data_type, data):
    if data_type == "Text/URL" and not data:
        return False, "Please enter Text or URL."
    elif data_type == "vCard":
        name, phone, email = data
        if not name or not phone:
            return False, "Name and phone number are required."
        if not re.match(r"^\+?\d{10,15}$", phone):
            return False, "Invalid phone number (use + followed by 10-15 digits)."
        if email and not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
            return False, "Invalid email address."
    elif data_type == "Email" and not data:
        return False, "Please enter an email address."
    return True, ""

# Initialize session state
if 'qr_buffer' not in st.session_state:
    st.session_state.qr_buffer = None
if 'qr_mime' not in st.session_state:
    st.session_state.qr_mime = None
if 'qr_file_ext' not in st.session_state:
    st.session_state.qr_file_ext = None
if 'qr_image' not in st.session_state:
    st.session_state.qr_image = None
if 'last_inputs' not in st.session_state:
    st.session_state.last_inputs = ""

# Tabs
tab1, tab2 = st.tabs(["Generate QR", "Scan QR"])

with tab1:
    st.subheader("Generate a QR Code")

    # QR code type selection
    qr_type = st.selectbox("QR Code Type", ["Text/URL", "vCard", "Email"])

    # Input fields
    qr_data = None
    if qr_type == "Text/URL":
        qr_data = st.text_input("Text or URL", placeholder="https://example.com")
    elif qr_type == "vCard":
        vcard_name = st.text_input("Name (Required)", placeholder="John Doe")
        vcard_phone = st.text_input("Phone (Required)", placeholder="+1234567890")
        vcard_email = st.text_input("Email (Optional)", placeholder="john@example.com")
        qr_data = (vcard_name, vcard_phone, vcard_email)
    elif qr_type == "Email":
        qr_data = st.text_input("Email Address", placeholder="contact@example.com")

    # Customization options
    fg_color = st.color_picker("QR Color", "#000000")
    bg_color = st.color_picker("Background Color", "#FFFFFF")
    scale = st.slider("Size", 1, 10, 5)
    error_correction = st.selectbox("Error Correction", ["L", "M", "Q", "H"], help="Use Q or H for logos to ensure scannability.")
    logo_file = st.file_uploader("Add Logo (PNG/JPG)", type=["png", "jpg", "jpeg"])
    file_format = st.selectbox("Download As", ["PNG", "JPG", "JPEG", "SVG"])

    # Check for input changes to clear session state
    current_inputs = f"{qr_type}{qr_data}{logo_file is not None}"
    if current_inputs != st.session_state.last_inputs:
        st.session_state.qr_buffer = None
        st.session_state.qr_mime = None
        st.session_state.qr_file_ext = None
        st.session_state.qr_image = None
        st.session_state.last_inputs = current_inputs

    # Preview placeholder
    preview_placeholder = st.empty()

    # Display preview if QR image exists
    if st.session_state.qr_image is not None and file_format in ["PNG", "JPG", "JPEG"]:
        preview_placeholder.image(st.session_state.qr_image, caption="QR Code Preview")

    # Generate QR button
    if st.button("Generate QR"):
        valid, error = validate_inputs(qr_type, qr_data)
        if not valid:
            st.error(error)
        else:
            buffer = io.BytesIO()
            qr = None
            if qr_type == "Text/URL":
                qr = segno.make(qr_data, error=error_correction.lower())
            elif qr_type == "vCard":
                name, phone, email = qr_data
                vcard_string = make_vcard_string(name, phone, email)
                qr = segno.make(vcard_string, error=error_correction.lower())
            elif qr_type == "Email":
                qr = segno.make(f"mailto:{qr_data}", error=error_correction.lower())

            if file_format in ["PNG", "JPG", "JPEG"]:
                qr.save(buffer, kind="png", scale=scale, dark=fg_color, quiet_zone=bg_color)
                qr_image = Image.open(buffer).convert("RGBA")
                if logo_file:
                    logo_img = Image.open(logo_file).convert("RGBA")
                    qr_size = qr_image.size[0]
                    logo_size = qr_size // 6  # Smaller logo for scannability
                    logo_img = logo_img.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                    pos = ((qr_size - logo_size) // 2, (qr_size - logo_size) // 2)
                    qr_image.paste(logo_img, pos, logo_img)
                # Crop QR
                img_array = np.array(qr_image.convert("RGB"))
                bg_rgb = tuple(int(bg_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                non_bg = np.any(img_array != bg_rgb, axis=2)
                rows, cols = np.where(non_bg)
                if len(rows) > 0 and len(cols) > 0:
                    qr_image = qr_image.crop((cols.min(), rows.min(), cols.max() + 1, rows.max() + 1))
                buffer = io.BytesIO()
                if file_format == "PNG":
                    qr_image.save(buffer, format="PNG")
                    mime = "image/png"
                    file_ext = "png"
                else:
                    qr_image.convert("RGB").save(buffer, format="JPEG", quality=95)
                    mime = "image/jpeg"
                    file_ext = "jpg" if file_format == "JPG" else "jpeg"
                st.session_state.qr_image = qr_image
                st.session_state.qr_buffer = buffer.getvalue()
                st.session_state.qr_mime = mime
                st.session_state.qr_file_ext = file_ext
                preview_placeholder.image(qr_image, caption="QR Code Preview")
            elif file_format == "SVG":
                qr.save(buffer, kind="svg", scale=scale, dark=fg_color, quiet_zone=bg_color)
                st.session_state.qr_buffer = buffer.getvalue()
                st.session_state.qr_mime = "image/svg+xml"
                st.session_state.qr_file_ext = "svg"
                st.session_state.qr_image = None

    # Display download button if QR data exists
    if st.session_state.qr_buffer is not None:
        st.download_button(
            label=f"Download {file_format}",
            data=st.session_state.qr_buffer,
            file_name=f"qr_code.{st.session_state.qr_file_ext}",
            mime=st.session_state.qr_mime,
            key=f"download_{uuid.uuid4()}"
        )
with tab2:
    st.subheader("Scan a QR Code")
    image_file = st.file_uploader("Upload QR Code Image", type=["png", "jpg", "jpeg"])
    if image_file:
        image = Image.open(image_file)
        img_array = np.array(image)
        decoded = decode(img_array)
        if decoded:
            st.write(f"**Hidden Message**: {decoded[0].data.decode('utf-8')}")
            st.image(image, caption="Uploaded QR Code")
        else:
            st.error("No QR code found! Please upload a valid QR image.")