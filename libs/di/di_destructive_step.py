# -*- coding: utf-8 -*-
# !/usr/bin/python
#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# 
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#

""" Destructive operations."""
import csv
import fcntl
import hashlib
import logging
import multiprocessing as mp
import os
import random
import time
from multiprocessing import Manager

import boto3

from config.s3 import S3_CFG
from libs.di import di_lib
from libs.di import di_params

logger = logging.getLogger(__name__)


def destructive_step():
    deletePercentage = di_params.deletePercentage
    sleepTimeInHrsInit = 1
    sleepTimeInHrsInBet = 0.5
    # destructiveTestList = ['test_sas_hba_fault','test_public_data_network_fault',
    # 'test_power_failure', 'test_sas_hba_fault','test_power_failure',
    # 'test_controller_a_faults', 'test_controller_b_faults']

    destructiveTestList = ['test_sas_hba_fault', 'test_sas_hba_fault']
    deletedObjectList = []
    numProcess = 5

    # Initial sleep
    logger.info("Sleeping for {} hrs".format(sleepTimeInHrsInit))
    logger.info("Init Sleep Start : {}".format(time.ctime()))
    time.sleep(sleepTimeInHrsInit * 60 * 60)
    logger.info("Init Sleep End : {}".format(time.ctime()))

    users = di_lib.read_iter_content_json()

    if os.path.exists(di_params.destructiveTestResult):
        os.remove(di_params.destructiveTestResult)
    if os.path.exists(di_params.deleteOpFileName):
        os.remove(di_params.deleteOpFileName)
    if os.path.exists(di_params.comDeleteOpFileName):
        os.remove(di_params.comDeleteOpFileName)
    # Create 10 s3 instances
    s3ObjectList = {}

    for user, keys in users.items():
        user_name = user
        access_key = keys[0]
        secret_key = keys[1]

        try:
            s3 = boto3.resource('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        except Exception as e:
            logger.info(
                f'could not create s3 object for user {user_name} with access key {access_key} secret key {secret_key} exception:{e}')

        s3ObjectList[user_name] = s3

    # For loop to trigger destructive test, read & delete data.
    for curDestructiveTest in destructiveTestList:
        # Get upload file
        uploadedData = []
        attempts = 0
        while attempts < 3:
            try:
                with open(di_params.uploadDoneFile, newline='') as f:
                    reader = csv.reader(f)
                    uploadedData = list(reader)
                break
            except Exception as e:
                attempts = attempts + 1
                time.sleep(20)

        if len(uploadedData) == 0:
            # print("uploaded data not found, existing script")
            logger.info("uploaded data not found, existing script")
            exit(1)
        if os.path.exists(di_params.deleteOpFileName):
            with open(di_params.deleteOpFileName, newline='') as f:
                reader = csv.reader(f)
                deletedObjectList = list(reader)

        # Remove Destruction Result file
        if os.path.exists(di_params.destructiveTestResult):
            os.remove(di_params.destructiveTestResult)

        # read object, check for checksum value.. then delete objects and update csv
        logger.info(f'Total uploaded items {len(uploadedData)}')
        k = (len(uploadedData) - len(deletedObjectList)) * deletePercentage // 100
        indicies = random.sample(range(len(uploadedData)), k)
        deleteList = [uploadedData[i] for i in indicies]
        newListLen = len(deleteList)
        logger.info(f'Total items to be deleted {newListLen}')
        jobs = []
        perProcessObj = int(newListLen / numProcess)
        logger.info(f'Per process object operations {perProcessObj}')

        with Manager() as manager:
            combinedDelList = manager.list()
            for i in range(numProcess):
                pList = deleteList[perProcessObj * i:perProcessObj * (i + 1)]
                p = mp.Process(target=destructionCheck, args=(pList, deletedObjectList, s3ObjectList, combinedDelList))
                jobs.append(p)
            p = mp.Process(target=destructionTrigger, args=(curDestructiveTest,))
            jobs.append(p)

            for p in jobs:
                p.start()
            for p in jobs:
                p.join()

            # Dump combined delete list to csv
            with open(di_params.comDeleteOpFileName, 'a', newline='') as myfile:
                wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
                wr.writerows(combinedDelList)

        if os.path.exists(di_params.destructiveTestResult):
            destructiveTestRes = []
            with open(di_params.destructiveTestResult, newline='') as f:
                reader = csv.reader(f)
                destructiveTestRes = list(reader)
            for item in destructiveTestRes:
                try:
                    testName = item[0]
                    # comp = item[0]
                    status = item[1]
                    if status.strip() == 'Pass':
                        logger.info(f'Destructive Test {curDestructiveTest} Passed')
                    else:
                        logger.error(f'Destructive Test {curDestructiveTest} Failed')
                except Exception as e:
                    logger.error(f'Error in parsing destructive test result csv')
        else:
            logger.error(f'Result summary csv file not found after running destructive test {curDestructiveTest}')

        # check if upload done or not, if not sleep & continue
        if os.path.exists(di_params.uploadFinishedFileName):
            logger.info("Existing script as upload script have finished uploading all objects")
            break
        else:
            logger.info("In between Sleep Start : {}".format(time.ctime()))
            logger.info("Sleeping for {} hrs".format(sleepTimeInHrsInBet))
            time.sleep(sleepTimeInHrsInBet * 60 * 60)
            logger.info("In between Sleep End : {}".format(time.ctime()))
            logger.info("Continuing with next destruction test")

    logger.info("Destructive operations completed, check if upload done completely")
    uploadFileFound = 1
    while (uploadFileFound):
        if os.path.exists(di_params.uploadFinishedFileName):
            uploadFileFound = 0
            os.remove(di_params.uploadFinishedFileName)
            logger.info("Upload done completely")
            break
        else:
            logger.info("Upload not yet done, waiting for 2 mins")
            time.sleep(2 * 60)

    # trigger readScript
    logger.info("Triggering read script")


def destructionTrigger(curDestructiveTest):
    logger.info(f'current destructive test is {curDestructiveTest}')
    if curDestructiveTest == 'test_sas_hba_fault':
        os.system(di_params.SAS_HBA_FAULT_CMD)
    elif curDestructiveTest == 'test_public_data_network_fault':
        os.system(di_params.PUBLIC_DATA_NETWORK_FAULT_CMD)
    elif curDestructiveTest == 'test_power_failure':
        os.system(di_params.POWER_FAILURE_FAULT_CMD)
    elif curDestructiveTest == 'test_controller_a_faults':
        os.system(di_params.CONTROLLER_A_FAULT_CMD)
    elif curDestructiveTest == 'test_controller_b_faults':
        os.system(di_params.CONTROLLER_B_FAULT_CMD)


def destructionCheck(uploadedData, deletedObjectList, s3ObjectList, combinedDelList):
    deletedObjectList1 = []
    for item in uploadedData:
        if item not in deletedObjectList:  # item: userid bucket obj checksum
            chSumRec = str(item[3])
            chSumRec = chSumRec.strip()
            s3 = s3ObjectList[item[0]]
            dwnSuccess = 0
            try:
                # s3.Bucket(item[1]).download_file(item[1], item[2])
                logger.info(f'Send download request for {item}')
                s3.meta.client.download_file(item[1], item[2], item[2])
                logger.info(f'download object successful : {item}')
                dwnSuccess = 1
            except Exception as e:
                print(e)
                logger.error(f'download failed for {item} with exception {e}')
                # exit(1)
            if dwnSuccess:
                checkSumRead = hashlib.md5(open(str(item[2]), 'rb').read()).hexdigest()
                if checkSumRead.strip() != str(item[3]):
                    # print("checksum mismatch: bucket {} object {}".format(item[1],item[2]))
                    logger.error(f'checksum mismatch for {item}, calculated checksum is {checkSumRead}')
                    # exit(1)
                rmLocalObject = "rm -rf ./" + str(item[2])
                os.system(rmLocalObject)

                logger.info(f'Send delete object {item}')
                try:
                    logger.info(f'Sending delete object {item}')
                    s3.meta.client.delete_object(Bucket=item[1], Key=item[2])
                    logger.info(f'Delete Successful {item}')
                except Exception as e:
                    logger.error(f'Delete failed for {item}')
                else:
                    deletedObjectList1.append(item)
                    combinedDelList.append(item)
                    logger.info(f'Added deleted object into delete list {item}')

    with open(di_params.deleteOpFileName, 'a', newline='') as myfile:
        wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
        fcntl.flock(myfile, fcntl.LOCK_EX)
        wr.writerows(deletedObjectList1)
        fcntl.flock(myfile, fcntl.LOCK_UN)
