import streamlit as st
import torch
import torch.nn as nn
from torchvision import models, transforms
import numpy as np
import cv2
from PIL import Image
import matplotlib.pyplot as plt
import time
import av
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import queue
import threading
import warnings
warnings.filterwarnings('ignore')

# Seitenkonfiguration
st.set_page_config(
    page_title="Live CNN Vision - Wie das Netzwerk sieht",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS für modernes Design
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 600;
    }
    .vision-container {
        background: #fff;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: 2px solid #3498db;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .layer-panel {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid #e74c3c;
    }
    .live-indicator {
        background: #e74c3c;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        display: inline-block;
        font-weight: bold;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
    .feature-map-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin: 1rem 0;
    }
    .feature-map-item {
        border: 2px solid #3498db;
        border-radius: 8px;
        padding: 5px;
        background: white;
    }
    .video-info {
        background: #e8f4fd;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid #3498db;
    }
</style>
""", unsafe_allow_html=True)

class SimpleCNNVisualizer:
    def __init__(self):
        # Einfacheres Modell für bessere Performance
        self.model = models.resnet18(pretrained=True)
        self.model.eval()
        self.activations = {}
        self.setup_hooks()
        
        # Transform
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
    def setup_hooks(self):
        """Setze Hooks um Feature-Maps zu erfassen"""
        def hook_fn(layer_name):
            def hook(module, input, output):
                self.activations[layer_name] = output.detach()
            return hook
        
        # Hooks für wichtige Ebenen
        self.model.conv1.register_forward_hook(hook_fn('conv1'))
        self.model.layer1.register_forward_hook(hook_fn('layer1')) 
        self.model.layer2.register_forward_hook(hook_fn('layer2'))
        self.model.layer3.register_forward_hook(hook_fn('layer3'))
        self.model.layer4.register_forward_hook(hook_fn('layer4'))
    
    def process_frame(self, frame):
        """Verarbeite einen Frame und gebe Feature-Maps zurück"""
        try:
            # Frame vorverarbeiten
            input_tensor = self.transform(frame).unsqueeze(0)
            
            # Forward pass
            with torch.no_grad():
                output = self.model(input_tensor)
            
            # Sammle Feature-Maps
            feature_maps = {}
            for layer_name in ['conv1', 'layer1', 'layer2', 'layer3', 'layer4']:
                if layer_name in self.activations:
                    # Nimm die ersten 8 Feature-Maps
                    layer_output = self.activations[layer_name][0]
                    # Normalisiere für Visualisierung
                    normalized = (layer_output - layer_output.min()) / (layer_output.max() - layer_output.min() + 1e-8)
                    # Nimm nur die ersten 8 Maps für Performance
                    feature_maps[layer_name] = normalized[:8].cpu().numpy()
            
            return {
                'success': True,
                'feature_maps': feature_maps,
                'original_frame': frame
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

def create_feature_map_display(feature_maps, layer_name, title):
    """Erstelle eine einfache Anzeige für Feature-Maps"""
    if layer_name not in feature_maps:
        return None
    
    try:
        maps = feature_maps[layer_name]
        num_maps = min(8, len(maps))
        
        fig, axes = plt.subplots(2, 4, figsize=(12, 6))
        axes = axes.flatten()
        
        for i in range(num_maps):
            if i < len(axes):
                axes[i].imshow(maps[i], cmap='viridis')
                axes[i].set_title(f'Feature {i+1}', fontsize=8)
                axes[i].axis('off')
        
        # Verstecke leere Subplots
        for i in range(num_maps, len(axes)):
            axes[i].axis('off')
        
        plt.suptitle(title, fontsize=12, fontweight='bold')
        plt.tight_layout()
        return fig
        
    except Exception as e:
        st.error(f"Error creating visualization: {e}")
        return None

class VideoProcessor:
    def __init__(self):
        self.visualizer = SimpleCNNVisualizer()
        self.frame_queue = queue.Queue(maxsize=1)
        self.result_queue = queue.Queue(maxsize=1)
        self.processing = False
        self.frame_count = 0
        self.start_time = time.time()
    
    def process_loop(self):
        """Verarbeitungsschleife"""
        while self.processing:
            try:
                frame = self.frame_queue.get(timeout=0.1)
                if frame is not None:
                    self.frame_count += 1
                    result = self.visualizer.process_frame(frame)
                    self.result_queue.put(result)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Processing error: {e}")
    
    def start(self):
        self.processing = True
        self.frame_count = 0
        self.start_time = time.time()
        self.thread = threading.Thread(target=self.process_loop)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        self.processing = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1.0)
    
    def get_fps(self):
        """Berechne aktuelle FPS"""
        if self.start_time > 0:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                return self.frame_count / elapsed
        return 0

def video_callback(frame: av.VideoFrame, processor: VideoProcessor) -> av.VideoFrame:
    """Frame Callback"""
    try:
        img = frame.to_ndarray(format="bgr24")
        try:
            processor.frame_queue.put_nowait(img)
        except queue.Full:
            pass
        return av.VideoFrame.from_ndarray(img, format="bgr24")
    except Exception as e:
        return frame

def main():
    st.markdown('<div class="main-header">Live CNN Vision - Layer Visualisierung</div>', unsafe_allow_html=True)
    
    # Einleitung
    st.markdown("""
    <div class="vision-container">
        <h2>Sehen Sie was das CNN in jedem Layer sieht!</h2>
        <p>Diese Anwendung zeigt live, wie ein Convolutional Neural Network (CNN) 
        Bilder verarbeitet. Jede Ebene erkennt unterschiedliche Merkmale.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialisiere Processor
    if 'processor' not in st.session_state:
        st.session_state.processor = VideoProcessor()
    
    processor = st.session_state.processor
    
    # Sidebar Steuerung
    st.sidebar.title(" Steuerung")
    
    # Layer Auswahl
    st.sidebar.markdown("### 📊 Layer Auswahl")
    show_conv1 = st.sidebar.checkbox("Conv1 Layer (Kanten/Farben)", value=True)
    show_layer1 = st.sidebar.checkbox("Layer1 (Einfache Formen)", value=True)
    show_layer2 = st.sidebar.checkbox("Layer2 (Texturen)", value=True)
    show_layer3 = st.sidebar.checkbox("Layer3 (Objekt-Teile)", value=False)
    show_layer4 = st.sidebar.checkbox("Layer4 (Komplette Objekte)", value=True)
    
    # Auto-Refresh
    auto_refresh = st.sidebar.checkbox("Auto-Refresh aktivieren", value=True)
    refresh_rate = st.sidebar.slider("Refresh Rate (ms)", 100, 2000, 500)
    
    # Hauptbereich
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class="vision-container">
            <h3>📹 Live Kamera</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # WebRTC Stream
        webrtc_ctx = webrtc_streamer(
            key="cnn-vision",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}),
            video_frame_callback=lambda frame: video_callback(frame, processor),
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True,
        )
    
    with col2:
        st.markdown("""
        <div class="layer-panel">
            <h3>📈 Status</h3>
        </div>
        """, unsafe_allow_html=True)
        
        status_placeholder = st.empty()
        info_placeholder = st.empty()
        video_info_placeholder = st.empty()
    
    # Starte/stoppe Verarbeitung
    if webrtc_ctx.state.playing:
        if not processor.processing:
            processor.start()
            status_placeholder.success("✅ Verarbeitung aktiv")
    else:
        if processor.processing:
            processor.stop()
        status_placeholder.warning("⏸Warte auf Kamera...")
    
    # Zeige Video-Informationen wenn aktiv
    if webrtc_ctx.state.playing and processor.processing:
        with video_info_placeholder.container():
            st.markdown("""
            <div class="video-info">
                <h4>📊 Video Informationen</h4>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("FPS", f"{processor.get_fps():.1f}")
            with col2:
                st.metric("Frames verarbeitet", processor.frame_count)
            with col3:
                st.metric("Verarbeitungszeit", f"{refresh_rate}ms")
    
    # Zeige Layer Visualisierungen
    if webrtc_ctx.state.playing and processor.processing:
        try:
            # Hole Ergebnis
            result = processor.result_queue.get_nowait()
            
            if result and result.get('success'):
                feature_maps = result['feature_maps']
                
                # Zeige Info
                with info_placeholder.container():
                    st.write(f"✅ {len(feature_maps)} Layer verarbeitet")
                    st.write("Bewegen Sie sich vor der Kamera!")
                
                # CONV1 LAYER - Kanten und Farben
                if show_conv1 and 'conv1' in feature_maps:
                    st.markdown("###  Conv1 Layer - Grundlegende Kanten und Farben")
                    st.write("**Was dieser Layer sieht:** Horizontale/vertikale Kanten, Farbübergänge, einfache Muster")
                    
                    fig = create_feature_map_display(
                        feature_maps, 
                        'conv1', 
                        'Conv1 Layer - Grundlegende Merkmale'
                    )
                    if fig:
                        st.pyplot(fig)
                        plt.close(fig)
                
                # LAYER1 - Einfache Formen
                if show_layer1 and 'layer1' in feature_maps:
                    st.markdown("###  Layer1 - Einfache Formen")
                    st.write("**Was dieser Layer sieht:** Kreise, Ecken, Bögen, grundlegende geometrische Formen")
                    
                    fig = create_feature_map_display(
                        feature_maps, 
                        'layer1', 
                        'Layer1 - Einfache Formen'
                    )
                    if fig:
                        st.pyplot(fig)
                        plt.close(fig)
                
                # LAYER2 - Texturen und Muster
                if show_layer2 and 'layer2' in feature_maps:
                    st.markdown("###  Layer2 - Texturen und Muster")
                    st.write("**Was dieser Layer sieht:** Felltexturen, Stoffmuster, Holzmaserungen, Oberflächen")
                    
                    fig = create_feature_map_display(
                        feature_maps, 
                        'layer2', 
                        'Layer2 - Texturen und Muster'
                    )
                    if fig:
                        st.pyplot(fig)
                        plt.close(fig)
                
                # LAYER3 - Objekt-Teile
                if show_layer3 and 'layer3' in feature_maps:
                    st.markdown("###  Layer3 - Objekt-Teile")
                    st.write("**Was dieser Layer sieht:** Augen, Räder, Türen, Fenster, Gesichtszüge")
                    
                    fig = create_feature_map_display(
                        feature_maps, 
                        'layer3', 
                        'Layer3 - Objekt-Teile'
                    )
                    if fig:
                        st.pyplot(fig)
                        plt.close(fig)
                
                # LAYER4 - Komplette Objekte
                if show_layer4 and 'layer4' in feature_maps:
                    st.markdown("###  Layer4 - Komplette Objekte")
                    st.write("**Was dieser Layer sieht:** Gesichter, Tiere, Fahrzeuge, Gebäude, komplette Szenen")
                    
                    fig = create_feature_map_display(
                        feature_maps, 
                        'layer4', 
                        'Layer4 - Komplette Objekte'
                    )
                    if fig:
                        st.pyplot(fig)
                        plt.close(fig)
                
                # Auto-Refresh
                if auto_refresh:
                    time.sleep(refresh_rate / 1000.0)
                    st.rerun()
                    
            else:
                if result:
                    st.error(f"Fehler: {result.get('error')}")
                
        except queue.Empty:
            # Kein neues Ergebnis verfügbar
            if auto_refresh:
                time.sleep(refresh_rate / 1000.0)
                st.rerun()
    
    else:
        # Zeige nur Anleitung wenn keine Kamera aktiv ist
        if not webrtc_ctx.state.playing:
            st.markdown("""
            <div class="vision-container">
                
            </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()