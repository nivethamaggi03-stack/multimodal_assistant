import os
import base64
import tempfile

from flask import (
    Flask,
    render_template,
    request
)
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

from llm import (
    describe_image,
    ask_about_image,
    generate_image
)


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)


# Maximum upload size: 20 MB
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024


# ============================================================
# ALLOWED IMAGE EXTENSIONS
# ============================================================

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
    "gif",
    "bmp",
    "tif",
    "tiff"
}


# ============================================================
# CHECK FILE EXTENSION
# ============================================================

def allowed_file(filename):

    if "." not in filename:
        return False

    extension = filename.rsplit(
        ".",
        1
    )[1].lower()

    return extension in ALLOWED_EXTENSIONS


# ============================================================
# CONVERT IMAGE FILE TO TEMPORARY FILE
# ============================================================

def save_uploaded_image(uploaded_file):

    if not uploaded_file:

        raise ValueError(
            "Please upload an image."
        )

    if not uploaded_file.filename:

        raise ValueError(
            "Please select an image file."
        )

    if not allowed_file(
        uploaded_file.filename
    ):

        raise ValueError(
            "Unsupported image format. "
            "Please upload JPG, JPEG, PNG, WEBP, "
            "GIF, BMP or TIFF."
        )

    original_filename = secure_filename(
        uploaded_file.filename
    )

    extension = os.path.splitext(
        original_filename
    )[1].lower()

    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=extension
    )

    uploaded_file.save(
        temp_file.name
    )

    temp_file.close()

    return temp_file.name


# ============================================================
# CONVERT UPLOADED IMAGE TO BASE64
# FOR IMAGE PREVIEW IN HTML
# ============================================================

def image_to_data_url(uploaded_file):

    if not uploaded_file:
        return None

    try:

        file_bytes = uploaded_file.read()

        uploaded_file.seek(0)

        encoded = base64.b64encode(
            file_bytes
        ).decode("utf-8")

        filename = uploaded_file.filename.lower()

        if filename.endswith(".jpg") or filename.endswith(".jpeg"):
            mime_type = "image/jpeg"

        elif filename.endswith(".png"):
            mime_type = "image/png"

        elif filename.endswith(".webp"):
            mime_type = "image/webp"

        elif filename.endswith(".gif"):
            mime_type = "image/gif"

        elif filename.endswith(".bmp"):
            mime_type = "image/bmp"

        elif filename.endswith(".tif") or filename.endswith(".tiff"):
            mime_type = "image/tiff"

        else:
            mime_type = "image/jpeg"

        return (
            f"data:{mime_type};base64,{encoded}"
        )

    except Exception:

        uploaded_file.seek(0)

        return None


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# IMAGE DESCRIPTION
# ============================================================

@app.route(
    "/describe",
    methods=["POST"]
)
def describe():

    uploaded_file = request.files.get(
        "image"
    )

    if not uploaded_file:

        return render_template(
            "index.html",
            description_error="Please upload an image first."
        )

    image_preview = image_to_data_url(
        uploaded_file
    )

    temp_path = None

    try:

        temp_path = save_uploaded_image(
            uploaded_file
        )

        result = ""

        for chunk in describe_image(
            temp_path
        ):

            result += chunk

        return render_template(
            "index.html",
            description=result,
            uploaded_image=image_preview
        )

    except Exception as e:

        return render_template(
            "index.html",
            description_error=str(e),
            uploaded_image=image_preview
        )

    finally:

        if temp_path and os.path.exists(
            temp_path
        ):

            os.remove(
                temp_path
            )


# ============================================================
# ASK QUESTION ABOUT IMAGE
# ============================================================

@app.route(
    "/ask",
    methods=["POST"]
)
def ask():

    uploaded_file = request.files.get(
        "image"
    )

    question = request.form.get(
        "question",
        ""
    ).strip()


    if not uploaded_file:

        return render_template(
            "index.html",
            question_error="Please upload an image first.",
            question=question
        )


    if not question:

        return render_template(
            "index.html",
            question_error="Please enter a question.",
            question=question
        )


    image_preview = image_to_data_url(
        uploaded_file
    )

    temp_path = None

    try:

        temp_path = save_uploaded_image(
            uploaded_file
        )

        answer = ""

        for chunk in ask_about_image(
            image_path=temp_path,
            question=question
        ):

            answer += chunk

        return render_template(
            "index.html",
            answer=answer,
            question=question,
            uploaded_image=image_preview
        )

    except Exception as e:

        return render_template(
            "index.html",
            question_error=str(e),
            question=question,
            uploaded_image=image_preview
        )

    finally:

        if temp_path and os.path.exists(
            temp_path
        ):

            os.remove(
                temp_path
            )


# ============================================================
# TEXT TO IMAGE
# ============================================================

@app.route(
    "/generate",
    methods=["POST"]
)
def generate():

    prompt = request.form.get(
        "prompt",
        ""
    ).strip()


    if not prompt:

        return render_template(
            "index.html",
            generation_error=(
                "Please enter a prompt."
            ),
            generation_prompt=prompt
        )


    try:

        generated = generate_image(
            prompt
        )


        # ----------------------------------------------------
        # Convert generated PIL image to PNG Base64
        # ----------------------------------------------------

        from io import BytesIO

        buffer = BytesIO()

        generated.save(
            buffer,
            format="PNG"
        )

        encoded_image = base64.b64encode(
            buffer.getvalue()
        ).decode("utf-8")


        generated_image = (
            "data:image/png;base64,"
            + encoded_image
        )


        return render_template(
            "index.html",
            generated_image=generated_image,
            generation_prompt=prompt
        )


    except Exception as e:

        return render_template(
            "index.html",
            generation_error=str(e),
            generation_prompt=prompt
        )


# ============================================================
# HANDLE LARGE FILE ERROR
# ============================================================

@app.errorhandler(413)
def file_too_large(error):

    return render_template(
        "index.html",
        description_error=(
            "The uploaded file is too large. "
            "Please upload an image smaller than 20 MB."
        )
    ), 413


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )