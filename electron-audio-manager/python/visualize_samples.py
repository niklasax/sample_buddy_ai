#!/usr/bin/env python3
import json
import os
import sys
import argparse
import numpy as np
from collections import defaultdict
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_samples(directory):
    """Load sample data from processed directories"""
    samples = []
    
    try:
        # Walk through directory structure to find all processed samples
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.json'):
                    try:
                        with open(os.path.join(root, file), 'r') as f:
                            sample_data = json.load(f)
                            # Add the sample path
                            if 'path' not in sample_data and 'original_path' in sample_data:
                                sample_data['path'] = sample_data['original_path']
                            samples.append(sample_data)
                    except json.JSONDecodeError:
                        logging.warning(f"Could not parse JSON from {os.path.join(root, file)}")
                    except Exception as e:
                        logging.error(f"Error loading sample {file}: {str(e)}")
    except Exception as e:
        logging.error(f"Error accessing directory {directory}: {str(e)}")
    
    logging.info(f"Loaded {len(samples)} samples from {directory}")
    return samples

def extract_feature_matrix(samples, features=None):
    """Extract feature matrix from samples"""
    if not features:
        # Default features to extract
        features = ['spectral_centroid', 'spectral_bandwidth', 'spectral_rolloff', 
                   'zero_crossing_rate', 'energy', 'tempo']
    
    # Collect all available features
    feature_values = defaultdict(list)
    valid_samples = []
    
    # Safety check for None samples
    if samples is None:
        logging.error("extract_feature_matrix received None samples")
        return None, None, features
    
    for sample in samples:
        # Skip samples without features
        if 'features' not in sample:
            logging.debug(f"Sample missing 'features' field: {sample.get('path', 'unknown path')}")
            continue
            
        # Get features dict, handling different data structures
        if isinstance(sample['features'], dict):
            features_dict = sample['features']
        elif isinstance(sample['features'], list) and len(sample['features']) > 0:
            # Assume it's a list of feature dicts, use the first one
            features_dict = sample['features'][0]
        elif sample.get('features') is None:
            # Handle None features by using minimal feature set
            logging.debug(f"Sample has None features: {sample.get('path', 'unknown path')}")
            
            # Try to create minimal features from other fields
            if 'category' in sample or 'mood' in sample:
                # Create synthetic features based on category/mood values
                features_dict = {
                    'spectral_centroid': 0.5,
                    'spectral_bandwidth': 0.5,
                    'spectral_rolloff': 0.5,
                    'zero_crossing_rate': 0.5,
                    'energy': 0.5,
                    'tempo': 120.0
                }
            else:
                continue
        else:
            logging.debug(f"Sample has invalid features format: {type(sample['features'])}")
            continue
            
        # Check if sample has all required features
        has_features = True
        for feature in features:
            if feature not in features_dict:
                has_features = False
                break
        
        if has_features:
            valid_samples.append(sample)
            for feature in features:
                feature_values[feature].append(float(features_dict[feature]))
    
    if not valid_samples:
        required_features_str = ', '.join(features)
        logging.warning(f"No valid samples with required features found. Required features: {required_features_str}")
        logging.warning(f"Processed {len(samples)} samples, but none had all required features")
        sample_stats = {}
        for feature in features:
            sample_stats[feature] = sum(1 for s in samples if 'features' in s and 
                                  isinstance(s['features'], dict) and feature in s['features'])
        logging.warning(f"Feature availability in samples: {sample_stats}")
        return None, None, None
    
    # Create the feature matrix
    X = np.zeros((len(valid_samples), len(features)))
    for i, feature in enumerate(features):
        X[:, i] = feature_values[feature]
    
    return X, valid_samples, features

def reduce_dimensions(X, method='pca', n_components=2, **kwargs):
    """Reduce dimensionality of feature matrix for visualization"""
    # Standardize features
    X_scaled = StandardScaler().fit_transform(X)
    
    # Apply dimensionality reduction
    if method.lower() == 'pca':
        model = PCA(n_components=n_components)
    elif method.lower() == 'tsne':
        perplexity = min(30, X.shape[0] - 1)  # Adjust perplexity based on sample count
        model = TSNE(n_components=n_components, perplexity=perplexity, **kwargs)
    else:
        raise ValueError(f"Unknown dimensionality reduction method: {method}")
    
    try:
        reduced = model.fit_transform(X_scaled)
        return reduced
    except Exception as e:
        logging.error(f"Error in dimensionality reduction: {str(e)}")
        return None

def map_features_directly(samples, x_feature, y_feature):
    """Map samples directly using two selected features without dimension reduction"""
    coordinates = []
    valid_samples = []
    
    for sample in samples:
        if 'features' not in sample:
            continue
            
        # Get features dict
        if isinstance(sample['features'], dict):
            features_dict = sample['features']
        elif isinstance(sample['features'], list) and len(sample['features']) > 0:
            features_dict = sample['features'][0]
        else:
            continue
            
        # Check if sample has required features
        if x_feature in features_dict and y_feature in features_dict:
            try:
                x_val = float(features_dict[x_feature])
                y_val = float(features_dict[y_feature])
                coordinates.append([x_val, y_val])
                valid_samples.append(sample)
            except (ValueError, TypeError):
                continue
    
    if not valid_samples:
        logging.warning(f"No valid samples with features {x_feature} and {y_feature}")
        return None, None
        
    coordinates = np.array(coordinates)
    
    # Normalize coordinates for better visualization
    x_min, x_max = coordinates[:, 0].min(), coordinates[:, 0].max()
    y_min, y_max = coordinates[:, 1].min(), coordinates[:, 1].max()
    
    if x_max > x_min:
        coordinates[:, 0] = (coordinates[:, 0] - x_min) / (x_max - x_min)
    if y_max > y_min:
        coordinates[:, 1] = (coordinates[:, 1] - y_min) / (y_max - y_min)
    
    return coordinates, valid_samples

def get_color_values(samples, color_feature):
    """Get values for coloring points based on a feature or category"""
    color_values = []
    
    if color_feature in ['category', 'mood']:
        # Use categorical values
        categories = {}
        category_count = 0
        
        for sample in samples:
            category = sample.get(color_feature, 'unknown').lower()
            if category not in categories:
                categories[category] = category_count
                category_count += 1
            color_values.append(categories[category])
            
        # Add category map to return normalized numeric values and their labels
        category_map = {v: k for k, v in categories.items()}
        return color_values, category_map
    else:
        # Use numeric feature values
        for sample in samples:
            if 'features' not in sample:
                color_values.append(0)
                continue
                
            # Get features dict
            if isinstance(sample['features'], dict):
                features_dict = sample['features']
            elif isinstance(sample['features'], list) and len(sample['features']) > 0:
                features_dict = sample['features'][0]
            else:
                color_values.append(0)
                continue
                
            if color_feature in features_dict:
                try:
                    color_values.append(float(features_dict[color_feature]))
                except (ValueError, TypeError):
                    color_values.append(0)
            else:
                color_values.append(0)
        
        # Normalize color values
        if color_values:
            min_val = min(color_values)
            max_val = max(color_values)
            if max_val > min_val:
                color_values = [(v - min_val) / (max_val - min_val) for v in color_values]
        
        return color_values, None

def create_visualization_data(samples, x_feature='spectral_centroid', y_feature='spectral_rolloff', 
                             color_feature='category', use_dimension_reduction=False):
    """Create visualization data for plotting samples"""
    result = {
        'success': False,
        'message': '',
        'data': {
            'points': [],
            'x_feature': x_feature,
            'y_feature': y_feature,
            'color_feature': color_feature
        }
    }
    
    if not samples:
        result['message'] = 'No samples provided'
        return result
    
    try:
        if use_dimension_reduction:
            # Use dimension reduction (PCA or t-SNE)
            feature_matrix, valid_samples, features = extract_feature_matrix(samples)
            if feature_matrix is None or valid_samples is None or len(valid_samples) < 2:
                result['message'] = 'Not enough valid samples with required features'
                return result
                
            coordinates = reduce_dimensions(feature_matrix, method='pca')
            if coordinates is None:
                result['message'] = 'Failed to reduce dimensions'
                return result
        else:
            # Map directly using selected features
            coordinates, valid_samples = map_features_directly(samples, x_feature, y_feature)
            if coordinates is None or valid_samples is None or len(valid_samples) < 1:
                total_samples = len(samples) if samples else 0
                samples_with_any_features = sum(1 for s in samples if 'features' in s and s.get('features')) if samples else 0
                
                # Provide a more helpful error message
                if samples_with_any_features == 0:
                    result['message'] = f'No samples with any features found. Try processing samples with deep analysis enabled.'
                else:
                    result['message'] = f'No samples with features "{x_feature}" and "{y_feature}" found ({samples_with_any_features}/{total_samples} have some features)'
                return result
        
        # Get color values
        color_values, category_map = get_color_values(valid_samples, color_feature)
        
        # Create points data
        points = []
        if valid_samples is None:
            valid_samples = []
            
        for i, sample in enumerate(valid_samples):
            # Create point data
            point = {
                'id': sample.get('id', str(i)),
                'name': os.path.basename(sample.get('path', f'sample_{i}')),
                'x': float(coordinates[i, 0]),
                'y': float(coordinates[i, 1]),
                'color_value': color_values[i] if i < len(color_values) else 0,
                'category': sample.get('category', 'unknown'),
                'mood': sample.get('mood', 'unknown'),
                'path': sample.get('path', '')
            }
            
            # Add feature values for tooltip
            if 'features' in sample:
                features_dict = sample['features']
                if isinstance(features_dict, list) and len(features_dict) > 0:
                    features_dict = features_dict[0]
                
                # Add the most important features to display
                feature_data = {}
                for feature in ['spectral_centroid', 'energy', 'tempo', 'zero_crossing_rate']:
                    if isinstance(features_dict, dict) and feature in features_dict:
                        try:
                            feature_data[feature] = features_dict.get(feature)
                        except Exception as e:
                            print(f"Error accessing feature {feature}: {e}")
                            continue
                point['features'] = feature_data
            
            points.append(point)
            
        result['data']['points'] = points
        result['data']['category_map'] = category_map
        result['success'] = True
        result['message'] = f'Successfully created visualization data for {len(points)} samples'
        
    except Exception as e:
        logging.error(f"Error creating visualization data: {str(e)}")
        result['message'] = f'Error: {str(e)}'
        
    return result

def load_samples_from_json(json_file):
    """Load samples directly from a JSON file"""
    try:
        with open(json_file, 'r') as f:
            samples = json.load(f)
        logging.info(f"Loaded {len(samples)} samples from {json_file}")
        return samples
    except Exception as e:
        logging.error(f"Error loading samples from JSON file {json_file}: {str(e)}")
        return []

def main():
    parser = argparse.ArgumentParser(description='Create 2D visualization data for audio samples')
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--input_dir', help='Directory containing processed sample data')
    input_group.add_argument('--input_file', help='JSON file with sample data')
    
    parser.add_argument('--output_file', help='Output JSON file (defaults to stdout)')
    parser.add_argument('--x_feature', default='spectral_centroid', help='Feature for X axis')
    parser.add_argument('--y_feature', default='spectral_rolloff', help='Feature for Y axis')
    parser.add_argument('--color_feature', default='category', help='Feature for coloring points')
    args = parser.parse_args()
    
    # Load samples
    if args.input_dir:
        samples = load_samples(args.input_dir)
    else:
        samples = load_samples_from_json(args.input_file)
    
    # Create visualization data
    result = create_visualization_data(
        samples, 
        x_feature=args.x_feature, 
        y_feature=args.y_feature,
        color_feature=args.color_feature
    )
    
    # Output results
    if args.output_file:
        with open(args.output_file, 'w') as f:
            json.dump(result, f, indent=2)
    else:
        print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()