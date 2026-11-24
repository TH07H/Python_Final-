## To run this program the audio files must be downloaded and saved as an MP3 file in the folder of the program 
## The slider does not work and will only serve to restart the song, this a bug that needs to be fixed in future updates 
## Have fun!
import numpy as np
import librosa
import pygame
import math


#Load audio file and excpetions 
while True:
    file_name = input("Enter the name of your audio file: ").strip()

    if not file_name.lower().endswith(".mp3"):
        file_name += ".mp3"

    try:
        audio, sample_rate = librosa.load(file_name, sr=None, mono=True)
        break

    except FileNotFoundError:
        print("Error: File not found. Please try again.")

    except Exception:
        print("Error: Invalid or unsupported MP3 file. Please try again.")
file_path = file_name



# Display audio information
duration = len(audio) / sample_rate
print("Sample Rate:", sample_rate)
print("Number of Samples:", len(audio))
print("Duration:", duration, "seconds")


# Exponential smoothing
alpha = 0.2
def exponential_smoothing(values, alpha):
    smoothed = [values[0]]
    for i in range(1, len(values)):
        current = values[i]
        previous = smoothed[i - 1]
        new_value = alpha * current + (1 - alpha) * previous
        smoothed.append(new_value)
    return smoothed


# FFT settings
frame_size = 8192
hop_size = 1024
window = np.hanning(frame_size)
frequencies = np.fft.rfftfreq(frame_size,d=1/sample_rate)
num_bars = 128
frequency_edges = np.geomspace(20, min(16000, sample_rate / 2), num_bars + 1)
spectrum_values = []


# Audio Proccesing 
for start in range(0, len(audio) - frame_size + 1, hop_size):

    frame = audio[start:start + frame_size]
    windowed_frame = frame * window
    fft_result = np.fft.rfft(windowed_frame)
    magnitude = np.abs(fft_result)
    bar_values = []

    for i in range(num_bars):
        frequency_range = ((frequencies >= frequency_edges[i]) & (frequencies < frequency_edges[i + 1]))
        # Avoid empty Freq ranges 
        if np.any(frequency_range):
            value = np.mean(magnitude[frequency_range])
        else:
            center_frequency = (frequency_edges[i] + frequency_edges[i + 1]) / 2
            nearest_bin = np.argmin(np.abs(frequencies - center_frequency))
            value = magnitude[nearest_bin]
        bar_values.append(value)
    spectrum_values.append(bar_values)

# Convert to NumPy array
spectrum_values = np.array(spectrum_values)
print("Spectrum Shape:", spectrum_values.shape)


# Normalize each frequency band independently
band_scale = np.percentile(spectrum_values, 85, axis=0)

#prevent almost 0 frquesncy from being read
minimum_scale = np.max(spectrum_values) * 0.01
band_scale = np.maximum(band_scale, minimum_scale)
spectrum_values = spectrum_values / (band_scale + 1e-10)
spectrum_values = np.clip(spectrum_values, 0, 1)

# Smooth each bar over time
smooth_spectrum = np.zeros_like(spectrum_values)

for i in range(num_bars):smooth_spectrum[:, i] = exponential_smoothing(spectrum_values[:, i], alpha)
print("Total Frames:", len(smooth_spectrum))
print("Number of Circular Bars:", num_bars)

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# settings
WIDTH = 900
HEIGHT = 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Circular Music Visualizer")
clock = pygame.time.Clock()

# Load and play audio
pygame.mixer.music.load(file_path)

# Playback settings
pygame.mixer.music.play()
playing = True
playback_position = 0
visual_mode = "Circular"

BLACK = (0, 0, 0)
BLUE = (40, 120, 255)
GREEN = (40, 220, 100)
ORANGE = (255, 150, 40)
WHITE = (255, 255, 255)

# Circle settings
center_x = WIDTH // 2
center_y = 260
inner_radius = 100
max_bar_length = 150

# Playback controls
mode_button_rect = pygame.Rect(20, 20, 150, 35)
button_rect = pygame.Rect(WIDTH // 2 - 45, 510, 90, 35)
slider_rect = pygame.Rect(100, 565, 700, 6)
dragging_slider = False
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Play/Pause button
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = event.pos
            if mode_button_rect.collidepoint(event.pos):
                visual_mode = "Equalizer" if visual_mode == "Circular" else "Circular"
            if button_rect.collidepoint(event.pos):
                if playing:
                    playback_position = pygame.mixer.music.get_pos() / 1000
                    pygame.mixer.music.pause()
                    playing = False
            
                else:
                    pygame.mixer.music.unpause()
                    playing = True

            # Click or drag the timeline
            if slider_rect.inflate(0, 25).collidepoint(event.pos):
                dragging_slider = True
                playback_position = ((mouse_x - slider_rect.x) / slider_rect.width) * duration
                playback_position = max(0, min(duration, playback_position))
                pygame.mixer.music.play(start=playback_position)
                playing = True

        if event.type == pygame.MOUSEBUTTONUP:
            dragging_slider = False

        if event.type == pygame.MOUSEMOTION and dragging_slider:
            mouse_x = event.pos[0]
            playback_position = ((mouse_x - slider_rect.x) / slider_rect.width) * duration
            playback_position = max(0, min(duration, playback_position))
            pygame.mixer.music.stop()
            pygame.mixer.music.play(start=playback_position)
            playing = True


    # Update playback position
    if playing:
        if pygame.mixer.music.get_busy():
            playback_position = (pygame.mixer.music.get_pos() / 1000)

        else:
            playing = False
            playback_position = duration

    # Convert playback time to FFT frame
    frame_index = int(playback_position * sample_rate / hop_size)
    frame_index = min(frame_index, len(smooth_spectrum) - 1)
    screen.fill(BLACK)
    font = pygame.font.SysFont(None, 24)

    # Draw visualizer
    if playing or playback_position < duration:
        if visual_mode == "Circular":
            for i in range(num_bars):
                value = np.nan_to_num(smooth_spectrum[frame_index, i],nan=0.0)
                bar_length = int(value * max_bar_length)
                angle = (2 * math.pi * i / num_bars) - math.pi / 2    
                start_x = center_x + math.cos(angle) * inner_radius
                start_y = center_y + math.sin(angle) * inner_radius
                end_x = center_x + math.cos(angle) * (inner_radius + bar_length)
                end_y = center_y + math.sin(angle) * (inner_radius + bar_length)
                frequency = (frequency_edges[i] + frequency_edges[i + 1]) / 2
    
                if frequency < 250:
                    color = BLUE
                elif frequency < 4000:
                    color = GREEN
                else:
                    color = ORANGE
    
                pygame.draw.line(screen,color,(int(start_x), int(start_y)),(int(end_x), int(end_y)),5)
            pygame.draw.circle(screen,WHITE,(center_x, center_y),inner_radius - 5,2)

        else:
            bar_width = WIDTH / num_bars
            max_height = 350
    
            for i in range(num_bars):
                value = np.nan_to_num(smooth_spectrum[frame_index, i],nan=0.0)
                bar_height = int(value * max_height)
                frequency = (frequency_edges[i] + frequency_edges[i + 1]) / 2
                if frequency < 250:
                    color = BLUE
                elif frequency < 4000:
                    color = GREEN
                else:
                    color = ORANGE
    
                x = int(i * bar_width)
                y = 450 - bar_height
    
                pygame.draw.rect(screen,color,(x, y, math.ceil(bar_width), bar_height))

    # Draw visualization mode button
    pygame.draw.rect(screen, WHITE, mode_button_rect, border_radius=5)
    mode_text = "Mode: " + visual_mode
    mode_surface = font.render(mode_text, True, BLACK)
    mode_rect = mode_surface.get_rect(center=mode_button_rect.center)
    screen.blit(mode_surface, mode_rect)
    
    
    
    # Draw Play/Pause button
    pygame.draw.rect(screen, WHITE, button_rect, border_radius=5)
    font = pygame.font.SysFont(None, 24)
    button_text = "Pause" if playing else "Play"
    text_surface = font.render(button_text, True, BLACK)
    text_rect = text_surface.get_rect(center=button_rect.center)
    screen.blit(text_surface, text_rect)

    # Draw timeline
    pygame.draw.rect(screen,WHITE,slider_rect,border_radius=5)
    slider_position = playback_position / duration
    slider_x = slider_rect.x + slider_position * slider_rect.width
    pygame.draw.circle(screen,BLUE,(int(slider_x), slider_rect.centery),9)

    # Draw time display
    current_time = int(playback_position)
    time_text = f"{current_time // 60:02}:{current_time % 60:02} / {int(duration) // 60:02}:{int(duration) % 60:02}"
    time_surface = font.render(time_text, True, WHITE)
    time_rect = time_surface.get_rect(center=(WIDTH // 2, 590))
    screen.blit(time_surface, time_rect)
    pygame.display.flip()
    clock.tick(60)

pygame.quit()

