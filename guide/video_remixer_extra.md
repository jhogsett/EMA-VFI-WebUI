**Video Remixer Extra** - Special Features and Project Clean Up

#### Split Scene - Split a Scene into two new scenes at a chosen moment

- **Used For:** Breaking up a scene without redoing project setup
- _Enter the scene ID for the scene to split and choose a percentage for the split point_
- _Splits the scene into two new scenes, and creates replacement thumbnails_
- _**Tip:**_
    - Use the _Split Scene_ button in the _Danger Zone_ from the Scene Chooser

#### Merge Scene Range - Merge a range of scenes

- **Used For:** Removing splits between scenes
- _Enter the starting and ending scene IDs_
- _All scenes from starting to ending scene ID are combined into a single scene_

#### Coalesce Scenes - Automatically merge adjacent kept scenes

- **Used For:** Automatically removing all splits between sets of kept scenes
- _Leave the checkbox unchecked to see which scenes will be merged_
- _All sets of adjacent kept scenes are merged into single scenes_

#### Choose Scene Range - Keep or Drop a range of scenes

- **Used For:** Quickly Keeping or Dropping a series of scenes
- _Enter the starting and ending scene IDs, and whether to Keep or Drop_
- _All scenes from starting to ending scene ID are set to the chosen state_

#### Drop Processed Scene - Drop a scene after processing has been already been done

- **Used For:** Removing a scene from the remix without having to reprocess content
- _Enter the scene ID to drop_
- _Sets the scene to_ Dropped _in the project and deletes all related processed content_

#### Cleanse Scenes - Remove noise and artifacts from kept scenes

- **Used For:** Cleaning scenes that are especially noisy or full of digital artifacts
- _Use Scene Chooser to Keep the frames that should be cleansed_
- _All kept scenes are upscaled 4X using Real-ESRGAN 4x+ then reduced 4X using "area" interpolation_
- _**Note:**_
    - The original scenes are purged to the _purged_content_ folder

#### Video Blend Scene - Use Video Blender to perform frame restoration

- **Used For:** Advanced frame restoration for heavly damaged content
- _Enter the scene ID to create a Video Blender project for_
- _You will be taken to the New Project page will pre-filled values_

#### Export Kept Scenes - Duplicate kept scenes to a new project

- **Used For:** Creating a new project from a set of kept scenes
- _Enter the path for storage and a name for the the new project_
- _All kept scenes and related thumbnails will be duplicated to the new project_
- _**Note:**_
    - The original source frames and dropped scenes are not duplicated

#### Import Scenes - Import scenes exported from the same source video

- **Used For:** Recombining scenes exported from the same source video
- _Enter the path to the project to import_
- _All scenes, scene states, scene labels and thumbnails will be imported_

#### Purge Processed Content - Soft-Delete processed content

- **Used For:** Setting aside previously processed content ahead of another processing round
- _Tips_
  - The accompanying `project.yaml` file is saved along with the purged content
  - Replace the main project content with this content to return to this project state
- _Processed remix video content is moved to a new directory in_ `purged_content`

#### Empty Purged Content - Permently deleted purged content

- **When Useful:** Always - frees disk space used for purged stale content
- _Check the box for the content to delete and click Delete Purged Content_
- _Content in the "purged_content" project directory is permanently deleted_

#### Delete All Project Content - Delete all generated project content (except videos)

- **When Useful:** After the project is complete and no longer needed - frees all disk space used by project-created content, except for source and remix videos
- _Check the box for the content to delete and click Delete Selected Content_
- _All project content except videos are permanently deleted_

#### Recover Deleted Project - Recreate a purged or corrupt project using the source video and project file

- **When Useful:** After a project's content has been purged, or if it has become corrupt - restores the project to an editable state
- _Click Recover Project_
- _The project's source frames, scenes and thumbnails are restored_

#### Remove Scene Chooser Content - Delete source PNG frame files, thumbnails and dropped scenes

- **When Useful:** Once final scene keep/drop choices are done - frees disk space used for source frames, thumbnails and dropped scenes
- _Check the box for the content to delete and click Delete Selected Content_
- _Source frames, thumbnails and/or dropped scenes are permanently deleted_

#### Remove Remix Video Source Content - Clear space after final Remix Videos have been saved

- **When Useful:** Once all versions of the remix video are final - frees disk space used for kept scenes, processed content, and remix clips
- _Check the box for the content to delete and click Delete Selected Content_
- _Kept scenes, processed content, and/or remix clips are permanently deleted_

