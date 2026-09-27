import sys

import cv2
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def image_to_scribble_detailed(input_path, output_path=None, show_result=True):
    """
    Convert an image to a detailed scribble-like drawing with internal texture
    
    Args:
        input_path (str): Path to input image
        output_path (str, optional): Path to save output image
        show_result (bool): Whether to display the result
    
    Returns:
        numpy.ndarray: The processed scribble image
    """
    
    # Read the image
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError(f"Could not load image from {input_path}")
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply histogram equalization to enhance contrast
    gray = cv2.equalizeHist(gray)
    
    # Multiple processing approaches for different types of detail
    
    # 1. Very light smoothing to preserve texture
    light_blur = cv2.GaussianBlur(gray, (3, 3), 0.5)
    
    # 2. More aggressive smoothing for major edges
    heavy_blur = cv2.GaussianBlur(gray, (15, 15), 0)
    
    # Edge detection with multiple sensitivity levels
    
    # High sensitivity edges (for texture and detail)
    edges_fine = cv2.Canny(light_blur, 20, 60)
    
    # Medium sensitivity edges 
    edges_medium = cv2.Canny(gray, 50, 120)
    
    # Low sensitivity edges (for main contours)
    edges_coarse = cv2.Canny(heavy_blur, 80, 160)
    
    # Sobel for directional texture
    sobelx = cv2.Sobel(light_blur, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(light_blur, cv2.CV_64F, 0, 1, ksize=3)
    sobel_combined = np.sqrt(sobelx**2 + sobely**2)
    sobel_combined = np.uint8(sobel_combined / sobel_combined.max() * 255)
    _, sobel_thresh = cv2.threshold(sobel_combined, 30, 255, cv2.THRESH_BINARY)
    
    # Laplacian for fine detail
    laplacian = cv2.Laplacian(light_blur, cv2.CV_64F, ksize=3)
    laplacian = np.uint8(np.absolute(laplacian))
    _, laplacian_thresh = cv2.threshold(laplacian, 15, 255, cv2.THRESH_BINARY)
    
    # Texture detection using local standard deviation
    kernel = np.ones((5,5), np.float32) / 25
    mean_img = cv2.filter2D(gray.astype(np.float32), -1, kernel)
    sqr_img = cv2.filter2D((gray.astype(np.float32))**2, -1, kernel)
    texture = np.sqrt(sqr_img - mean_img**2)
    texture = np.uint8(texture / texture.max() * 255)
    _, texture_thresh = cv2.threshold(texture, 20, 255, cv2.THRESH_BINARY)
    
    # Combine all edge types with different weights
    combined_edges = np.zeros_like(gray)
    
    # Add fine details (weighted more heavily)
    combined_edges = cv2.add(combined_edges, edges_fine)
    combined_edges = cv2.add(combined_edges, laplacian_thresh)
    combined_edges = cv2.add(combined_edges, texture_thresh)
    
    # Add medium details
    combined_edges = cv2.add(combined_edges, edges_medium // 2)
    combined_edges = cv2.add(combined_edges, sobel_thresh // 2)
    
    # Add coarse details (main contours)
    combined_edges = cv2.add(combined_edges, edges_coarse)
    
    # Threshold the combined result
    _, combined_edges = cv2.threshold(combined_edges, 100, 255, cv2.THRESH_BINARY)
    
    # Apply morphological operations for organic variation
    kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    kernel_medium = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    
    # Create variations in line thickness
    thick_lines = cv2.morphologyEx(combined_edges, cv2.MORPH_DILATE, kernel_medium, iterations=1)
    thin_lines = cv2.morphologyEx(combined_edges, cv2.MORPH_ERODE, kernel_small, iterations=1)
    
    # Randomly combine thick and thin lines for variation
    height, width = combined_edges.shape
    variation_mask = np.random.rand(height, width)
    
    final_edges = combined_edges.copy()
    final_edges[variation_mask > 0.7] = thick_lines[variation_mask > 0.7]
    final_edges[variation_mask < 0.3] = thin_lines[variation_mask < 0.3]
    
    # Add some random scribble-like noise in areas with existing edges
    edge_pixels = final_edges > 0
    noise_candidates = cv2.dilate(edge_pixels.astype(np.uint8), kernel_small, iterations=2)
    noise_mask = (noise_candidates > 0) & (np.random.rand(height, width) > 0.85)
    final_edges[noise_mask] = 255
    
    # Clean up very small isolated components
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(final_edges, connectivity=8)
    min_size = 10  # Minimum component size to keep
    
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] < min_size:
            final_edges[labels == i] = 0
    
    # Invert so we have black lines on white background
    scribble_image = 255 - final_edges
    
    # Display the result
    if show_result:
        plt.figure(figsize=(20, 5))
        
        plt.subplot(1, 4, 1)
        plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        plt.title('Original Image')
        plt.axis('off')
        
        plt.subplot(1, 4, 2)
        plt.imshow(edges_fine, cmap='gray')
        plt.title('Fine Detail Edges')
        plt.axis('off')
        
        plt.subplot(1, 4, 3)
        plt.imshow(combined_edges, cmap='gray')
        plt.title('Combined Edges (White lines)')
        plt.axis('off')
        
        plt.subplot(1, 4, 4)
        plt.imshow(scribble_image, cmap='gray')
        plt.title('Final Detailed Scribble')
        plt.axis('off')
        
        plt.tight_layout()
        plt.show()
    
    # Save the result if output path is provided
    if output_path:
        cv2.imwrite(output_path, scribble_image)
        print(f"Detailed scribble image saved to: {output_path}")
    
    return scribble_image

def simple_texture_scribble(input_path, output_path=None, show_result=True):
    """
    Simpler approach focused on texture and internal detail
    """
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError(f"Could not load image from {input_path}")
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Enhance contrast
    gray = cv2.equalizeHist(gray)
    
    # Multiple Canny edge detection with different parameters
    edges1 = cv2.Canny(gray, 10, 30)  # Very sensitive
    edges2 = cv2.Canny(gray, 30, 80)  # Medium
    edges3 = cv2.Canny(gray, 80, 160) # Less sensitive
    
    # Combine them
    combined = cv2.bitwise_or(edges1, edges2)
    combined = cv2.bitwise_or(combined, edges3)
    
    # Add texture using local variance
    kernel = np.ones((7,7), np.float32) / 49
    mean_val = cv2.filter2D(gray.astype(np.float32), -1, kernel)
    sqr_val = cv2.filter2D((gray.astype(np.float32))**2, -1, kernel)
    variance = sqr_val - mean_val**2
    
    # Threshold variance to get texture regions
    _, texture_mask = cv2.threshold(variance, np.percentile(variance, 70), 255, cv2.THRESH_BINARY)
    texture_mask = texture_mask.astype(np.uint8)
    
    # Add texture to edges
    final_edges = cv2.bitwise_or(combined, texture_mask)
    
    # Morphological operations for line variation
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    final_edges = cv2.morphologyEx(final_edges, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # Invert
    scribble_image = 255 - final_edges
    
    if show_result:
        plt.figure(figsize=(15, 5))
        
        plt.subplot(1, 3, 1)
        plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        plt.title('Original')
        plt.axis('off')
        
        plt.subplot(1, 3, 2)
        plt.imshow(texture_mask, cmap='gray')
        plt.title('Texture Detection')
        plt.axis('off')
        
        plt.subplot(1, 3, 3)
        plt.imshow(scribble_image, cmap='gray')
        plt.title('Final Scribble')
        plt.axis('off')
        
        plt.tight_layout()
        plt.show()
    
    if output_path:
        cv2.imwrite(output_path, scribble_image)
        print(f"Scribble saved to: {output_path}")
    
    return scribble_image

# Example usage
if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python main.py <image>")
    input_image = sys.argv[1]
    
    try:
        # Try the detailed version first
        print("Generating detailed scribble...")
        detailed_result = image_to_scribble_detailed(input_image, "dog_detailed_scribble.png")
        
        # Also try the simpler texture-focused version
        print("Generating texture-focused scribble...")
        simple_result = simple_texture_scribble(input_image, "dog_simple_scribble.png")
        
    except FileNotFoundError:
        print(f"Image not found: {input_image}")
