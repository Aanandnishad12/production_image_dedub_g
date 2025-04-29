import cv2
import numpy as np
from skimage.measure import shannon_entropy

def calculate_laplace_variance(image):
    laplacian = cv2.Laplacian(image, cv2.CV_64F)
    return laplacian.var()

def calculate_contrast(image):
    return image.std()

def calculate_edge_density(image):
    edges = cv2.Canny(image, 100, 200)
    return np.count_nonzero(edges) / edges.size

def calculate_entropy(image):
    return shannon_entropy(image)

def calculate_quality_score(image_binary):
    """Calculate the quality score from an image stored in binary format."""
    # Convert binary data to a NumPy array
    image_array = np.frombuffer(image_binary, dtype=np.uint8)

    # Decode the image from memory
    image = cv2.imdecode(image_array, cv2.IMREAD_GRAYSCALE)

    # Ensure the image is loaded properly
    if image is None:
        raise ValueError("❌ Error: Could not decode image from binary data.")

    # Compute quality metrics
    laplace_var = calculate_laplace_variance(image)
    contrast = calculate_contrast(image)
    edge_density = calculate_edge_density(image)
    entropy = calculate_entropy(image)

    # Weighted score calculation
    score = (0.4 * laplace_var) + (0.2 * contrast) + (0.2 * edge_density) + (0.2 * entropy)

    return score
