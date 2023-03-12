"""Video Blender UI elements and event handlers"""
import csv
import os

class VideoBlenderPath:
    """Manages a set of project frame files"""
    def __init__(self, path : str):
        self.path = path
        self.files = sorted(os.listdir(self.path))
        self.last_frame = len(self.files) - 1
        self.load_file_info()

    def load_file_info(self):
        """Load information about the frames files into memory"""
        files = sorted(os.listdir(self.path))
        self.files = [os.path.join(self.path, file) for file in files]
        self.file_count = len(self.files)

    def get_frame(self, frame : int):
        """Return the filepath of an individual frame file"""
        if frame < 0 or frame > self.last_frame:
            return None
        return self.files[frame]

class VideoBlenderProjects:
    """Manages a set of projects"""
    FIELDS = ["project_name", "project_path", "frames1_path", "frames2_path"]

    def __init__(self, csvfile_path):
        self.csvfile_path = csvfile_path
        self.projects = {}
        self.read_projects()

    def read_projects(self):
        """Load project information from CSV file"""
        if os.path.isfile(self.csvfile_path):
            reader = csv.DictReader(open(self.csvfile_path, encoding="utf-8"))
            entries = list(reader)
            for entry in entries:
                project_name = entry["project_name"]
                self.projects[project_name] = entry

    def write_projects(self):
        """Save project information to CSV file"""
        project_names = self.get_project_names()
        row_array = [self.projects[project_name] for project_name in project_names]
        with open(self.csvfile_path, 'w', encoding="utf-8", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames = self.FIELDS)
            writer.writeheader()
            writer.writerows(row_array)

    def get_project_names(self):
        """Return a list of saved project names"""
        return list(self.projects.keys())

    def load_project(self, project_name : str):
        """Load project info by project name"""
        return self.projects[project_name]

    def save_project(self, project_name : str,
                    project_path : str,
                    frames1_path : str,
                    frames2_path : str):
        """Add a new saved project"""
        self.projects[project_name] = {
            "project_name" : project_name,
            "project_path" : project_path,
            "frames1_path" : frames1_path,
            "frames2_path" : frames2_path
        }
        self.write_projects()

class VideoBlenderState:
    """Manage the active state of a loaded project"""

    # which_path index into the path info list
    PROJECT_PATH = 0
    FRAMES1_PATH = 1
    FRAMES2_PATH = 2

    def __init__(self, project_path : str, frames_path1 : str, frames_path2 : str):
        self.project_path = project_path
        self.frames_path1 = frames_path1
        self.frames_path2 = frames_path2
        self.current_frame = 0
        self.path_info = [
            VideoBlenderPath(project_path),
            VideoBlenderPath(frames_path1),
            VideoBlenderPath(frames_path2)
            ]

    def get_frame_file(self, which_path : int, frame : int):
        """Get a frame file given a frame number and project path type"""
        return self.path_info[which_path].get_frame(frame)

    def get_frame_files(self, frame : int):
        """Get a set of frame files for Frame Chooser UI given a frame number"""
        results = []
        results.append(self.get_frame_file(self.FRAMES1_PATH, frame))
        results.append(self.get_frame_file(self.PROJECT_PATH, frame - 1))
        results.append(self.get_frame_file(self.PROJECT_PATH, frame))
        results.append(self.get_frame_file(self.PROJECT_PATH, frame + 1))
        results.append(self.get_frame_file(self.FRAMES2_PATH, frame))
        return results

    def goto_frame(self, frame : int):
        """Set the current frame and get a set of frame files for Frame Chooser UI"""
        self.current_frame = frame
        return self.get_frame_files(frame)
