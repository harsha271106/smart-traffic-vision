import pandas as pd
import matplotlib.pyplot as plt
import os

def generate_performance_plots(csv_file='traffic_performance_log.csv'):
    if not os.path.exists(csv_file):
        print(f"Error: Could not find '{csv_file}'. Run 'intersection_manager.py' first to collect data!")
        return

    # Read CSV Data
    df = pd.read_csv(csv_file)
    
    # Set up dark styled plot dashboard
    plt.style.use('dark_background')
    fig, axs = plt.subplots(2, 2, figsize=(14, 8))
    fig.suptitle('Smart Traffic Vision - Performance & Performance Analytics', fontsize=16, fontweight='bold', color='#58a6ff')

    # 1. Multi-Lane Density Trends over Time
    axs[0, 0].plot(df['Frame_Index'], df['Lane1_Density'], label='Lane 1', color='#e74c3c', alpha=0.8)
    axs[0, 0].plot(df['Frame_Index'], df['Lane2_Density'], label='Lane 2', color='#2ecc71', alpha=0.8)
    axs[0, 0].plot(df['Frame_Index'], df['Lane3_Density'], label='Lane 3', color='#3498db', alpha=0.8)
    axs[0, 0].plot(df['Frame_Index'], df['Lane4_Density'], label='Lane 4', color='#f1c40f', alpha=0.8)
    axs[0, 0].set_title('Vehicle Density per Lane (px count)', color='white')
    axs[0, 0].set_xlabel('Frame Index')
    axs[0, 0].set_ylabel('Pixel Count')
    axs[0, 0].legend(loc='upper right')
    axs[0, 0].grid(True, linestyle='--', alpha=0.3)

    # 2. Frame Processing Latency (ms)
    axs[0, 1].plot(df['Frame_Index'], df['Latency_ms'], color='#9b59b6', linewidth=1.5)
    axs[0, 1].axhline(y=df['Latency_ms'].mean(), color='#e67e22', linestyle='--', label=f"Mean: {df['Latency_ms'].mean():.2f} ms")
    axs[0, 1].set_title('System Processing Latency (ms/frame)', color='white')
    axs[0, 1].set_xlabel('Frame Index')
    axs[0, 1].set_ylabel('Latency (ms)')
    axs[0, 1].legend(loc='upper right')
    axs[0, 1].grid(True, linestyle='--', alpha=0.3)

    # 3. Signal Green Light Distribution Across Lanes
    green_counts = df['Active_Green_Lane'].value_counts().sort_index()
    lane_labels = [f"Lane {int(i)}" for i in green_counts.index]
    bars = axs[1, 0].bar(lane_labels, green_counts.values, color=['#e74c3c', '#2ecc71', '#3498db', '#f1c40f'])
    axs[1, 0].set_title('Green Signal Time Allocation Frequency', color='white')
    axs[1, 0].set_xlabel('Lane')
    axs[1, 0].set_ylabel('Total Active Frames')
    axs[1, 0].grid(axis='y', linestyle='--', alpha=0.3)

    # Add count labels above bars
    for bar in bars:
        yval = bar.get_height()
        axs[1, 0].text(bar.get_x() + bar.get_width()/2.0, yval + 5, int(yval), ha='center', va='bottom', color='white', fontsize=9)

    # 4. Average Density vs. Active Signal Allocation
    avg_densities = [df['Lane1_Density'].mean(), df['Lane2_Density'].mean(), df['Lane3_Density'].mean(), df['Lane4_Density'].mean()]
    lanes = ['Lane 1', 'Lane 2', 'Lane 3', 'Lane 4']
    axs[1, 1].barh(lanes, avg_densities, color=['#e74c3c', '#2ecc71', '#3498db', '#f1c40f'])
    axs[1, 1].set_title('Average Traffic Load per Lane', color='white')
    axs[1, 1].set_xlabel('Mean Pixel Density')
    axs[1, 1].grid(axis='x', linestyle='--', alpha=0.3)

    plt.tight_layout()
    
    # Save chart image for inclusion in case study report
    output_img = 'traffic_analytics_plot.png'
    plt.savefig(output_img, dpi=300)
    print(f"Analytics plot generated and saved as '{output_img}'.")
    plt.show()

if __name__ == "__main__":
    generate_performance_plots()