
from pypylon import pylon
import platform
import cv2
import os
from datetime import datetime
import numpy as np
import re

top_cam_srl = '24335316' # acA2500-14uc
btm_cam_srl = '40310345' # a2A3840-45ucBAS
data_folder = 'C:'+os.sep+"Users"+os.sep+'renrum'+os.sep+"Pictures"+os.sep+'Data'+os.sep
top_cam_ref = (1252, 890)
btm_cam_ref = (1888, 972)
top_cam_scale = 35.93 #pixel/mm
btm_cam_scale = 67.2 #pixel/mm

def take_img(cam: str, filename='', save_dir=None):
    try:
        if cam.lower() == 'top':
            camera_srl = top_cam_srl
        elif cam.lower() == 'btm':
            camera_srl = btm_cam_srl
        di = pylon.DeviceInfo()
        di.SetSerialNumber(camera_srl)

        # Initialize the camera
        tlf = pylon.TlFactory.GetInstance()
        devices = tlf.EnumerateDevices([di,])

        if not len(devices):
            print(f"Camera not found.")
            return

        camera = pylon.InstantCamera(tlf.CreateDevice(devices[0]))
        camera.Open()
        if cam.lower() == 'top':
            camera.AutoTargetBrightness.Value = 0.3
        elif cam.lower() == 'btm':
            camera.AutoTargetBrightness.Value = 0.3
        camera.AutoFunctionROISelector.Value = "ROI1"
        camera.AutoFunctionROIUseBrightness.Value = True
        camera.AutoFunctionROIUseWhiteBalance.Value = True
        camera.BalanceWhiteAuto.Value = "Continuous"
        camera.ExposureAuto.Value = "Continuous"
        camera.GainAuto.Value = "Continuous"

        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        # Retrieve the next available image
        grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        pylon_img = pylon.PylonImage()
        pylon_img.AttachGrabResultBuffer(grab_result)

        default_filename = datetime.today().strftime("%Y-%m-%d_%H-%M-%S")

        if filename:
            filename += '_'+default_filename+'_'+cam.lower()
        else:
            filename = default_filename
        if platform.system() == 'Windows':
            # Save as JPEG with adjustable quality (100 -> best quality, 0 -> poor quality)
            ipo = pylon.ImagePersistenceOptions()
            quality = 95
            ipo.SetQuality(quality)
            filename += ".jpg"
        else:
            # Save as PNG
            filename += ".png"

        # Check if a custom save directory is specified
        if save_dir:
            filename = os.path.join(save_dir, filename)
        else:
            date = datetime.today().strftime('%Y-%m-%d')
            if not os.path.exists(data_folder+date):
                os.makedirs(data_folder+date)
            filename = os.path.join(data_folder, date, filename)
        
        # Save the image
        pylon_img.Save(pylon.ImageFileFormat_Jpeg, filename, ipo) if platform.system() == 'Windows' else pylon_img.Save(pylon.ImageFileFormat_Png, filename)

        # Release the image to reuse the grab result
        pylon_img.Release()

        # Stop grabbing and close the camera
        camera.StopGrabbing()
        camera.Close()
        return filename

    except Exception as e:
        print(f"Error: {str(e)}")

# Example usage
#take_img(btm_cam_srl)

def fit_ellipse_to_image_path(image_path):
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    blurred = cv2.GaussianBlur(image, (5, 5), 0)
    edges = cv2.Canny(blurred, 20, 120)

    # Find contours (retrieve all contours)
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours based on area
    largest_contour = None
    max_area = 0
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > max_area:
            max_area = area
            largest_contour = contour

    if largest_contour is not None:
        # Fit the smallest enclosing circle
        (x, y), radius = cv2.minEnclosingCircle(largest_contour)
        center = (int(x), int(y))
        radius = int(radius)

        # Draw the fitted circle on the original image
        cv2.circle(image, center, radius, (0, 255, 0), 2)

        print(f"Center: ({center[0]}, {center[1]})")
        print(f"Radius: {radius:.2f} pixels")

        # Save the result
        cv2.imwrite("circle_result.jpg", image)
        cv2.imwrite("threshold.jpg", edges)
    else:
        print("No suitable contour found.")


def find_outer_circle(image_path, minrad, maxrad, mindis=100, camera=None, p1=150, p2=25, filename=''):
    # Load the image
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    padded_crop = np.full(image.shape, 255, np.uint8)
    # Get Center ROI
    crop_factor = 0.5
    x_center = image.shape[0]//2
    y_center = image.shape[1]//2
    crop = int(crop_factor*y_center)
    padded_crop[x_center-crop:x_center+crop, y_center-crop:y_center+crop] = image[x_center-crop:x_center+crop, y_center-crop:y_center+crop]

    gray = cv2.cvtColor(padded_crop, cv2.COLOR_BGR2GRAY)
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Detect circles using HoughCircles
    circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1, minDist=mindis,
                               param1=p1, param2=p2, minRadius=minrad, maxRadius=maxrad)

    if circles is not None:
        circles = np.uint16(np.around(circles))
        max_circle = None
        max_radius = 0
        for circle in circles[0]:
            center = (circle[0], circle[1])
            radius = circle[2]
            if radius > max_radius:
                max_circle = circle
                max_radius = radius

        # Draw the fitted circle on the original image
        cv2.circle(image, (max_circle[0], max_circle[1]), max_radius, (0, 255, 0), 25)
        cv2.line(image, (max_circle[0]-5, max_circle[1]), (max_circle[0]+5, max_circle[1]), (0, 255, 0), 35)
        cv2.line(image, (max_circle[0], max_circle[1]-5), (max_circle[0], max_circle[1]+5), (0, 255, 0), 35)

        # Draw ideal centerpoint on the original image if camera specified
        if camera:
            if camera.lower() == 'top':
                cv2.line(image, (top_cam_ref[0]-10, top_cam_ref[1]), (top_cam_ref[0]+10, top_cam_ref[1]), (0, 0, 255), 25)
                cv2.line(image, (top_cam_ref[0], top_cam_ref[1]-10), (top_cam_ref[0], top_cam_ref[1]+10), (0, 0, 255), 25)
            elif camera.lower() == 'btm':
                cv2.line(image, (btm_cam_ref[0]-25, btm_cam_ref[1]), (btm_cam_ref[0]+25, btm_cam_ref[1]), (0, 0, 255), 25)
                cv2.line(image, (btm_cam_ref[0], btm_cam_ref[1]-25), (btm_cam_ref[0], btm_cam_ref[1]+25), (0, 0, 255), 25)

        # Put text for fitted circle on the original image
        cv2.putText(image, f'Fitted Centerpoint: ({max_circle[0]}, {max_circle[1]})', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        if camera:
            if camera.lower() == 'top':
                cv2.putText(image, f'Approx. Diameter: {max_radius * 2/top_cam_scale:.1f} mm', (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            elif camera.lower() == 'btm':
                cv2.putText(image, f'Approx. Diameter: {max_radius * 2/btm_cam_scale:.1f} mm', (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        else:
            cv2.putText(image, f'Approx. Diameter: {max_radius * 2:.1f} pixels', (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        # Put text of offset on the original image
        if camera:
            if camera.lower() == 'top':
                cv2.putText(image, f'Offset from Center: ({max_circle[0] - top_cam_ref[0]}, {max_circle[1] - top_cam_ref[1]})', (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            elif camera.lower() == 'btm':
                cv2.putText(image, f'Offset from Center: ({max_circle[0] - btm_cam_ref[0]}, {max_circle[1] - btm_cam_ref[1]})', (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        #print(f"Center coordinates: ({max_circle[0]}, {max_circle[1]})")
        #print(f"Diameter: {max_radius * 2/35.93:.2f} mm")

        # Save the result
        filename = image_path.split('.')
        cv2.imwrite(filename[0]+'_fit.jpg', image)
        return (max_circle[0] - btm_cam_ref[0], max_circle[1] - btm_cam_ref[1])
    else:
        print("No suitable circle found.")

def cam_offset_to_robot(offset, robot:str)-> np.ndarray:
    if offset:
        scale = btm_cam_scale
        if robot.lower() == 'grip':
            theta = 2.3425016430693795-np.pi/2
            transform_mat = np.array([[np.cos(theta)/scale, -np.sin(theta)/scale],
                                      [np.sin(theta)/scale, np.cos(theta)/scale]])
        elif robot.lower() == 'crimp':
            theta = 0.014967151233958547#-3*np.pi/2
            transform_mat = np.array([[-np.cos(theta)/scale, -np.sin(theta)/scale],
                                      [np.sin(theta)/scale, np.cos(theta)/scale]])
        else:
            return np.pad(np.array([0.0, 0.0]), (0, 2), 'constant')

        
        transform_mat = np.array([[np.cos(theta)/scale, -np.sin(theta)/scale],
                              [np.sin(theta)/scale, np.cos(theta)/scale]])
        robot_coord = np.matmul(offset, transform_mat)
        return np.pad(np.round(robot_coord, decimals=2), (0, 2), 'constant')
    else:
        return np.pad(np.array([0.0, 0.0]), (0, 2), 'constant')

def get_cam_temp(cam: str):
    if cam.lower() == 'top':
        camera_srl = top_cam_srl
        print('top camera does not have temperature function')
        return
    elif cam.lower() == 'btm':
        camera_srl = btm_cam_srl
    di = pylon.DeviceInfo()
    di.SetSerialNumber(camera_srl)

        # Initialize the camera
    tlf = pylon.TlFactory.GetInstance()
    devices = tlf.EnumerateDevices([di,])

    if not len(devices):
        print(f"Camera not found.")
        return

    camera = pylon.InstantCamera(tlf.CreateDevice(devices[0]))
    camera.Open()
    d = camera.DeviceTemperature.Value
    return d

def find_latest_top_img(file_path):
    file_directory, filename = file_path.rsplit('\\', 1)
    filename_split = filename.split('.')[0].split('_')
    if 'btm' in filename_split or 'fit' in filename_split:
        print('passed')
        pass
    else:
        prefix = filename_split[0]
        ref_time = os.path.getmtime(file_path)
        pattern = re.compile(r'^'+prefix+r'_.*_top\.jpg$')
        matching_files = [f for f in os.listdir(file_directory) if pattern.match(f)]
        check_files = []
        check_times = []
        for n in matching_files:
            check_file = os.path.join(file_directory, n)
            if os.path.isfile(check_file):
                check_time = os.path.getmtime(check_file)
                time_diff = check_time - ref_time
                if time_diff < 0:
                    check_files.append(check_file)
                    check_times.append(abs(time_diff))
        try:
            closest_time_index = check_times.index(min(check_times))
            return check_files[closest_time_index]
        except ValueError:
            pass


def get_similarity(img1, img2):
    def crop_img(image_path, crop_factor = 0.45):
        """Crops an image starting from the center outward by the crop_factor"""
        image = cv2.imread(image_path, cv2.IMREAD_COLOR)
        padded_crop = np.full(image.shape, 255, np.uint8)
        x_center = image.shape[0]//2
        y_center = image.shape[1]//2
        crop = int(crop_factor*y_center)
        padded_crop[x_center-crop:x_center+crop, y_center-crop:y_center+crop] = image[x_center-crop:x_center+crop, y_center-crop:y_center+crop]
        return padded_crop
    def mse(imageA, imageB):
        """Compute the Mean Squared Error (MSE) between two images."""
        err = np.sum((imageA.astype("float") - imageB.astype("float")) ** 2)
        err /= float(imageA.shape[0] * imageA.shape[1])
        return err
    
    crop_first = crop_img(img1)
    crop_second = crop_img(img2)
    mse_value = (mse(crop_first[:, :, 0], crop_second[:, :, 0]) +
                 mse(crop_first[:, :, 1], crop_second[:, :, 1]) +
                 mse(crop_first[:, :, 2], crop_second[:, :, 2])) / 3
    return mse_value

#paths = take_img('btm')
#print(paths)
#paths = r"C:\Users\renrum\Pictures\Data\2024-04-20\2024-04-20_20-43-47.jpg"
#results = find_outer_circle(paths, 100, 300, 100, 'btm') # P casing 650, 680, 100
#print(np.round(cam_offset_to_robot(results,'crimp'), decimals=2)*-1)
#print(np.linalg.norm(cam_offset_to_robot((-18, 48), 'grip')))