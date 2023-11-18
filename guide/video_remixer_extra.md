**Video Remixer Extra** - Special Features and Project Clean Up

#### Split Scene - Split a Scene into two new scenes at a chosen moment

- **Used For:** Breaking up a scene without redoing project setup
- _Enter the scene ID for the scene to split and choose a percentage for the split point_
- _Splits the scene into two new scenes, and creates replacement thumbnails_
- _**Tip:**_
    - Use the _Split Scene_ button in the _Danger Zone_ from the Scene Chooser

#### Choose Scene Range - Keep or Drop a range of scenes

- **Used For:** Quickly Keeping or Dropping a series of scenes
- _Enter the starting and ending scene IDs, and whether to Keep or Drop_
- _All scenes from starting to ending scene ID are set to the chosen state_

#### Cleanse Scenes - Remove noise and artifacts from kept scenes

- **Used For:** Cleaning scenes that are especially noisy or full of digital artifacts
- _Use Scene Chooser to Keep the frames that should be cleansed_
- _All kept scenes are upscaled 4X using Real-ESRGAN 4x+ then reduced 4X using "area" interpolation_
- _**Note:**_
    - The original scenes are purged to the _purged_content_ folder

#### Drop Processed Scene - Drop a scene after processing has been already been done

- **Used For:** Removing a scene from the remix without having to reprocess content
- _Enter the scene ID to drop_
- _Sets the scene to_ Dropped _in the project and deletes all related processed content_

#### Export Kept Scenes - Duplicate kept scenes to a new project

- **Used For:** Creating a new project from a set of kept scenes
- _Enter the path for storage and a name for the the new project_
- _All kept scenes and related thumbnails will be duplicated to the new project_
- _**Note:**_
    - The original source frames and dropped scenes are not duplicated

#### Manage Storage - Free Disk Space by Removing Unneeded Content

#### Remove Soft-Deleted Content - Delete content set aside when remix processing selections are changed

- **When Useful:** Always - frees disk space used for purged stale content
- _Check the box for the content to delete and click Delete Purged Content_
- _Content in the "purged_content" project directory is permanently deleted_

#### Remove Scene Chooser Content - Delete source PNG frame files, thumbnails and dropped scenes

- **When Useful:** Once final scene keep/drop choices are done - frees disk space used for source frames, thumbnails and dropped scenes
- _Check the box for the content to delete and click Delete Selected Content_
- _Source frames, thumbnails and/or dropped scenes are permanently deleted_

#### Remove Remix Video Source Content - Clear space after final Remix Videos have been saved

- **When Useful:** Once all versions of the remix video are final - frees disk space used for kept scenes, processed content, and remix clips
- _Check the box for the content to delete and click Delete Selected Content_
- _Kept scenes, processed content, and/or remix clips are permanently deleted_

#### Remove All Processed Content - Delete all processed project content (except videos)

- **When Useful:** After the project is complete and no longer needed - frees all disk space used by project-created content, except for source and remix videos
- _Check the box for the content to delete and click Delete Selected Content_
- _All project content except videos are permanently deleted_

#### Recover Project - Recreate a purged or corrupt project using the source video and project file

- **When Useful:** After a project's content has been purged, or if it has become corrupt - restores the project to an editable state
- _Click Recover Project_
- _The project's source frames, scenes and thumbnails are restored_
