**Enhance Frames** - Auto-Correct Contrast for PNG Files

## What It Does

* Automatically improves contrast of PNG frame files
* Uses _Constrast Limited Adaptive Histogram Equalization_

## How It Works
1. Choose a _Correction Threshold_ or leave the default
    - The default value 2.0 may be useful in general cases
    - **Note:** The best value requires experimentation
1. Choose _Individual_ or _Batch Processing_
    - If **Individual Path**
        - Set _Input Path_ to a path on this server to the PNG files being enhanced
        - Set _Output Path_ to a path on this server for the enhanced PNG files
    - If **Batch Processing**
        - Set _Input Path_ to a directory on this server containing PNG frame groups to be enhanced
        - Set _Output Path_ to a directory on this server for the enhanced PNG frame groups
1. Click _Enhance_ or _Enhance Batch_
