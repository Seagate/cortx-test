#!/usr/bin/python3
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#

import binascii


MAGIC_HEADER = b'33011ca5e511de77'
MAGIC_FOOTER = b'33f007e7f007e777'

typeDict = {b'01': 'RPC_PACKET', b'02': 'RPC_ITEM', b'03': 'BE_BTREE',
                  b'04': 'BE_BNODE', b'05': 'BE_EMAP_KEY', b'06': 'BE_EMAP_REC',
                  b'07': 'BE_EMAP', b'08': 'BE_LIST', b'09': 'BE_SEG_HDR',
                  b'0a': 'BALLOC', b'0b': 'ADDB2_FRAME_HEADER', b'0c': 'STOB_AD_0TYPE_REC',
                  b'0d': 'STOB_AD_DOMAIN', b'0e': 'COB_DOMAIN', b'0f': 'COB_NSREC',
                  b'10': 'BALLOC_GROUP_DESC', b'11': 'EXT', b'12': 'CAS_INDEX',
                  b'13': 'POOLNODE', b'14': 'POOLDEV', b'15': 'POOL_SPARE_USAGE',
                  b'16': 'CAS_STATE', b'17': 'CAS_CTG', b'22': 'WRONG_ENTRY', b'44': 'WRONG_ENTRY'}

record_type_dict = {'BE_BTREE': [], 'BE_BNODE': [], 'BE_EMAP_KEY': [], 'BE_EMAP_REC': [],
                      'BE_EMAP': [], 'BE_LIST': [], 'BE_SEG_HDR': [], 'BALLOC': [],
                  'STOB_AD_0TYPE_REC': [], 'STOB_AD_DOMAIN': [], 'COB_DOMAIN': [],
                  'COB_NSREC': [], 'BALLOC_GROUP_DESC': [], 'EXT': [], 'POOLNODE': [],
                  'POOLDEV': [], 'POOL_SPARE_USAGE': [], 'CAS_STATE': [], 'CAS_CTG': [],
                  'EXTRA': []}

m0_btree_types = {b'01': "M0_BT_INVALID", b'02': "M0_BT_BALLOC_GROUP_EXTENTS", b'03': "M0_BT_BALLOC_GROUP_DESC",
                  b'04': "M0_BT_EMAP_EM_MAPPING", b'05': "M0_BT_CAS_CTG", b'06': "M0_BT_COB_NAMESPACE", b'07': "M0_BT_COB_OBJECT_INDEX",
                  b'08': "M0_BT_COB_FILEATTR_BASIC", b'09': "M0_BT_COB_FILEATTR_EA", b'0a': "M0_BT_COB_FILEATTR_OMG",
                  b'0b': "M0_BT_COB_BYTECOUNT", b'0c': "M0_BT_CONFDB", b'0d': "M0_BT_UT_KV_OPS", b'0e': "M0_BT_NR"}

m0_btree_types_dict={"M0_BT_INVALID":[], "M0_BT_BALLOC_GROUP_EXTENTS":[],"M0_BT_BALLOC_GROUP_DESC":[],"M0_BT_EMAP_EM_MAPPING":[],"M0_BT_CAS_CTG":[],"M0_BT_COB_NAMESPACE":[],"M0_BT_COB_OBJECT_INDEX":[],"M0_BT_COB_FILEATTR_BASIC":[],"M0_BT_COB_FILEATTR_EA":[],"M0_BT_COB_FILEATTR_OMG":[],"M0_BT_COB_BYTECOUNT":[],"M0_BT_CONFDB":[],"M0_BT_UT_KV_OPS":[],"M0_BT_NR":[]}


bnt_h_node_type = {b'00000001': 'FF', b'00000002': 'FKVV', b'00000003': 'VKFV', b'00000004': 'VKVV'}


class metadata_parser():
    """Meta data parser library"""

    def __init__(self, filename):
        """
        initialize all dictionaries
        """
        self.ff_dict = {}
        self.fkvv_dict = {}
        self.vkvv_dict = {}
        self.emap_key_dict={}
        self.BeBnodeTypeKeys={}
        self.filename=filename


    def ReadTypeSize(self, byte):
        """
        Function to extract record type and footer offset
        It will return record type and offset
        """
        # ver = byte[:4]   # Version
        rtype = byte[6:8]  # Record type
        size = byte[8:16]  # Node size as in node start offset + size = fmt footer offset
        return rtype, size


    def fmt_seg_header_parser(self, offset):
        """
        Format and segment header parser function
        """
        with open(self.filename, "rb") as md:
            md.seek(offset)
            hd_magic = binascii.hexlify((md.read(8))[::-1])
            hd_bits = binascii.hexlify((md.read(8))[::-1])
            h_type = binascii.hexlify((md.read(8))[::-1])
            h_tree_type = h_type[:8]
            h_tree_type = h_tree_type[6:8]
            h_node_type = h_type[8:] 
            h_crc_type = binascii.hexlify((md.read(8))[::-1])
            h_gen = binascii.hexlify((md.read(8))[::-1])
            h_fid = binascii.hexlify((md.read(16))[::-1])
            h_opaque = binascii.hexlify((md.read(8))[::-1])
            
            if(h_tree_type in m0_btree_types):
                m0_btree_types_dict[m0_btree_types[h_tree_type]].append(offset)
        
            #print(f"Node_header: [Header start offset: {offset}, hd_magic:{hd_magic}, hd_bits:{hd_bits}, h_node_type: {h_node_type}, h_tree_type: {h_tree_type}, h_crc_type: {h_crc_type}, h_gen: {h_gen}, h_fid: {h_fid}, h_opaque: {h_opaque}]")
            #balloc->4096, ctg-> 65536, cob-> 8192, emap-> 16384, confd->4096, dtm->8192 
            if h_tree_type in [b'02',b'03']:
                r_offset = offset + 4096
            elif h_tree_type in [b'04']:
                r_offset = offset + 16384
            elif h_tree_type in [b'05']:
                r_offset = offset + 65536
            elif h_tree_type in [b'07',b'08',b'09',b'0a',b'0b']:
                r_offset = offset + 8192
            elif h_tree_type in [b'0c']:
                r_offset = offset + 4096
            elif h_tree_type in [b'0e']:
                r_offset = offset + 8192
            else:
                r_offset = offset + 8
        return r_offset
    

    def get_emap_length(self):
        """
        Find length of emap entries in m0_btree_type
        return length of emap entries
        """
        return len(m0_btree_types_dict['M0_BT_EMAP_EM_MAPPING'])
    

    def get_fkvv_used(self,offset):
        """
        It will find the fkvv used count
        input - offset of fkvv
        return fkvv_used
        """
        with open(self.filename, "rb") as md:
            md.seek(offset)
            fkvv_first_pack = binascii.hexlify((md.read(8))[::-1]) # read level, ksize and all in single read
            fkvv_used = fkvv_first_pack[12:16]
        return fkvv_used
    

    def emap_key_parser(self, offset):
        """
        EMAP KEY PARSER, It will store EMAP key related data like node offset, size, length
        return emap key dictionary
        """
        cnt = 1
        fkvv_used=self.get_fkvv_used(offset+64)
        fkvv_nsize=b'00004000'

        if self.fkvv_parser(offset+64):
            with open(self.filename, "rb") as md:
                r_offset=offset + 104
                node_start_offset = offset
                while int(fkvv_used, 16) >= cnt:
                    md.seek(r_offset)
                    emap_key_header = binascii.hexlify(((md.read(8)))[::-1])
                    emap_key_hd_bits = binascii.hexlify(((md.read(8)))[::-1])
                    rec_type, rec_size = self.ReadTypeSize(emap_key_hd_bits)
                    ek_prefix = binascii.hexlify(((md.read(16)))[::-1])
                    ek_offset = binascii.hexlify(((md.read(8)))[::-1])
                    ek_footer = binascii.hexlify(((md.read(8)))[::-1])
                    ek_chksum = binascii.hexlify(((md.read(8)))[::-1])
                    value_offset = binascii.hexlify(((md.read(4)))[::-1])
                    #print(f"[****fkvv_key_start_offset: {node_start_offset}, emap_key_header: {emap_key_header}, rec_type: {rec_type}, rec_size: {rec_size} key prefix: {ek_prefix}, ek_offset: {ek_offset}, ek_footer: {ek_footer}, ek_chksum: {ek_chksum}, value_offset: {value_offset}]")
                    emap_key_offset = r_offset
                    node_length = fkvv_nsize
                    key_index = cnt
                    #value_offset = binascii.hexlify(((md.read(4)))[::-1])
                    #value_offset = value_offset[8:]
                    emap_key_list = [key_index, node_start_offset, emap_key_offset, int(node_length, 16), int(value_offset, 16)]
                    #print(f"*** Respective emap_key_list: {emap_key_list}")
                    self.emap_key_dict.setdefault(node_start_offset,[]).append(emap_key_list) 
                    cnt = cnt + 1
                    r_offset = r_offset + 60
        else:
            print("Cannot parse as it is not leaf fkvv node")
            #assert "Cannot parse as node is not FKVV"
        return self.emap_key_dict

    def ff_parser(self, offset):
        """
        FF header parser
        returns offset and length of header
        """
        total_node_header_len = 0
        ff_nsize = b'0'
        with open(self.filename, "rb") as md:
            md.seek(offset)
            ff_first_pack = binascii.hexlify((md.read(8))[::-1]) # read ff used, ff level, ff k_size, ff vsize and first byte of ff nsize
            ff_used = ff_first_pack[12:16] # 2 bytes ff used
            ff_level = ff_first_pack[10:12] # ff level 1 byte
            ff_ksize = ff_first_pack[6:10]  # ksize 2 byte
            ff_vsize = ff_first_pack[2:6] # vsize 2 byte
            ff_second_pack = binascii.hexlify((md.read(8))[::-1]) # read next 8 bytes first 3 of nsize and remaining of ftmagic
            ff_nsize = ff_second_pack[10:16]+ff_first_pack[:2] # nsize 1 byte from firstpack and 3 bytes from second pack
            ff_third_pack = binascii.hexlify((md.read(8))[::-1]) # read next 8 bytes first 3 of ft_magic and remaining of ft_checksum
            ft_magic = ff_third_pack[10:16]+ff_second_pack[:10] # ft_magic 3 bytes of third pack and 5 of second pack
            ff_fourth_pack = binascii.hexlify((md.read(8))[::-1]) # read next 8 bytes first 3 bytes of ft_checksum and remaining of ft_opaque
            ft_checksum = ff_fourth_pack[10:16]+ff_third_pack[:10] # ft_checksum 3 bytes of fourth pack and 5 from third pack      
            ff_last_pack = binascii.hexlify((md.read(3))[::-1]) # read remaining bytes of ft_opaque
            ft_opaque = ff_last_pack[:6] + ff_fourth_pack[:10] # ft_checksum 3 bytes of last pack and 5 from fourth pack
            print(f"[ff start offset:{offset}, ff_used: {ff_used}, ff_level:{ff_level}, ff_ksize:{ff_ksize}, ff_vsize:{ff_vsize}, ff_nsize:{ff_nsize}, ff_ft_magic:{ft_magic}, ff_ft_checksum:{ft_checksum}, ff_ft_opaque:{ft_opaque}]")
            if ff_level == b'0000' and ff_used != b'0000' and ft_magic == MAGIC_FOOTER:
                print("At Leaf FF level Zero node. So reading further...")
                self.ff_dict[offset] = [offset, ff_nsize, ff_used]
                key_start_offset = offset + 35
                r_offset=offset+35
            else:
                print(f"Leaf node level is non zero: {ff_level} or ff_used is Zero {ff_used}, So skipping collecting data")
                r_offset = offset + 35
        total_node_header_len = int(ff_nsize, 16) if int(ff_nsize, 16) > 0 else 35
        return r_offset, total_node_header_len

    def fkvv_parser(self,offset):
        """
        FKVV header parser
        returns offset and length of header
        """
        total_node_header_len = 0
        fkvv_nsize = b'0'
        with open(self.filename, "rb") as md:
            md.seek(offset)
            fkvv_first_pack = binascii.hexlify((md.read(8))[::-1]) # read level, ksize and all in single read
            fkvv_used = fkvv_first_pack[12:16]                     # used 2 bytes valid entry
            fkvv_level = fkvv_first_pack[8:12]                     # level 1 byte + 1 byte pad
            fkvv_ksize = fkvv_first_pack[:8]                       # kzise 2 bytes + 2 byte pad
            fkvv_nsize = binascii.hexlify((md.read(8))[::-1])      # total Node size 4 nsize and 4 byte padding
            fkvv_nsize = fkvv_nsize[8:]                            # read First 4 bytes for node size
            ft_magic = binascii.hexlify((md.read(8))[::-1])        # magic Footer 8 bytes
            ft_checksum = binascii.hexlify((md.read(8))[::-1])     # checksum     8 bytes
            ft_opaque = binascii.hexlify((md.read(8))[::-1])       # opaque       8 bytes

            if fkvv_level == b'0000' and fkvv_used != b'0000' and ft_magic == MAGIC_FOOTER:
                # print(f"[fkvv start offset:{offset}, fkvv_used: {fkvv_used}, fkvv_level:{fkvv_level}, fkvv_ksize:{fkvv_ksize}, fkvv_nsize:{fkvv_nsize}, ft_magic:{ft_magic}, ft_checksum:{ft_checksum}, ft_opaque:{ft_opaque}]")
                return True
            else:
                return False


    def vkvv_parser(self,offset):
        """
        VKVV header parser
        returns offset and length of header
        """
        print("vkvv",offset)


    def vkfv_parser(self,offset):
        """
        VKFV header parser
        returns offset and length of header
        """
        print("vkfv",offset)


    def read_metadata_file(self):
        '''
        Metadata read file function
        '''
        offset: int = 0
        with open(self.filename, "rb") as metadata:
            while 1:
                byte = metadata.read(8)
                if not byte:
                    break
                byte = binascii.hexlify(byte[::-1])
                if byte == MAGIC_HEADER:
                    offset= self.fmt_seg_header_parser(offset)
                else:
                    offset = offset + 8
                metadata.seek(offset)
                #if offset > 83886080: 270469216 134217728 16777216 2097152 262144  131070# Increase this number for reading more location in metadata
                if offset > 270469216: # :  # Increase this number for reading more location in metadata
                    break


    def EditEmapMetadata(self, emap_rec_full, offset, crc_offset):
        """Edit emap metadata with the fixed pattern of 0x1111222244443333."""
        with open(self.filename, 'r+b') as wbfr:
            print("** Corrupting 8byte of Metadata at offset {}"
                        " with b'1111222244443333' **".format(offset))
            wbfr.seek(offset)
            wbfr.flush()
            wbfr.write(b'\x33\x33\x44\x44\x22\x22\x11\x11')
            emap_rec_full[7] = '1111222244443333'
            val = self.ComputeCRC(emap_rec_full, len(emap_rec_full) - 2)
            print("Newly computed CRC : ", hex(val), " val to byte : ", val.to_bytes(8, 'little'),
                " offset : ", offset, " crc offset : ", crc_offset)
            wbfr.seek(crc_offset)
            wbfr.write(val.to_bytes(8, 'little'))
            wbfr.flush()
            wbfr.seek(offset)
            wbfr.flush()

    def ReadMetadata(self, offset):
        """Verifies that meta-data contains the valid footer at the given offset."""
        with open(self.filename, "rb") as mdata:
            mdata.seek(offset)
            data = binascii.hexlify((mdata.read(8))[::-1])
            if data == MAGIC_FOOTER:
                return True, data
            return False, data


    def ReadCompleteRecord(self, offset):
        """Function read complete record starting after header and until footer for record."""
        curr_record = []
        while 1:
            footerFound, data = self.ReadMetadata(offset)
            if footerFound:
                break
            curr_record.append(data.decode('utf-8'))
            offset = offset + 8  # check next 8 bytes

        # Convert list to hex representation
        curr_record = [hex(int(i, 16)) for i in curr_record]
        return curr_record, offset  # Return record data and footer offset


    def ReadCompleteRecordIncCRC(self, offset):
        """Function read complete record starting after header and until footer for record."""
        curr_record = []
        while 1:
            footerFound, data = self.ReadMetadata(offset)
            curr_record.append(data.decode('utf-8'))
            offset = offset + 8  # check next 8 bytes
            if footerFound:
                _, data = self.ReadMetadata(offset)
                curr_record.append(data.decode('utf-8'))
                offset = offset + 8
                break

        # Convert list to hex representation
        # curr_record = [ hex(int(i, 16)) for i in curr_record]
        return curr_record, offset  # Return record data and footer offset

    @staticmethod
    def m0_hash_fnc_fnv1(buffer, length):
        ptr = buffer
        val = 14695981039346656037
        mask = (1 << 64) - 1
        if buffer == None or length == 0:
            return 0
        for i in range(round(length / 8)):
            for j in reversed(range(7 + 1)):
                val = (val * 1099511628211) & mask
                val = val ^ ptr[(i * 8) + j]
                val = val & mask
        return val

    def ComputeCRC(self, string_list, list_len):
        result = []
        for i in range(list_len):
            byte_array = bytes.fromhex(string_list[i])
            for j in byte_array:
                result.append(j)
        val = self.m0_hash_fnc_fnv1(result, len(result))
        return val

    @staticmethod
    def ConvertAdstob2Cob(stob_f_container, stob_f_key):
        """Method to extract cob related data."""
        M0_FID_DEVICE_ID_OFFSET = 32
        M0_FID_DEVICE_ID_MASK = 72057589742960640
        M0_FID_TYPE_MASK = 72057594037927935

        # m0_fid_tassume()
        tid = int(67)  # Char 'C' Ascii Value
        cob_f_container = ((tid << (64 - 8)) | (int(stob_f_container, 16) & M0_FID_TYPE_MASK))
        cob_f_key = int(stob_f_key, 16)
        device_id = (int(cob_f_container) & M0_FID_DEVICE_ID_MASK) >> M0_FID_DEVICE_ID_OFFSET

        return cob_f_container, cob_f_key, device_id

    @staticmethod
    def ConvertCobAdstob(cob_f_container, cob_f_key):
        """Method take cob_f_cotainer, cob_f_key and returns stob_f_container, stob_f_key."""
        M0_FID_TYPE_MASK = 72057594037927935

        # m0_fid_tassume()
        tid = 2  # STOB_TYPE_AD = 0x02
        stob_f_container = ((tid << (64 - 8)) | (int(cob_f_container, 16) & M0_FID_TYPE_MASK))
        stob_f_key = int(cob_f_key, 16)

        return stob_f_container, stob_f_key


    def CorruptEmap(self, emap_entry):
        """Method corrupts EMAP record specified by Cob ID."""
        count = 0
        stob_f_container, stob_f_key = emap_entry.split(":")
        stob_f_container = hex(int(stob_f_container, 16))
        stob_f_key = hex(int(stob_f_key, 16))
        print(f"stob_f_container: {stob_f_container}, stob_f_key: {stob_f_key}")
        #stop_f_key_1 = "0x{:02x}".format(stob_f_key[2:])
        emap_keys_list = self.ListAllEmapPerDevice()
        emap_key = [
            key 
            for key in emap_keys_list 
            if stob_f_container in key and (stob_f_key in key)
            ]

        offset = emap_key[0][1]
        emap_key_data, r_offset = self.ReadCompleteRecord(offset)

        if (stob_f_container in emap_key_data) and \
                (stob_f_key or stob_f_key_1 in emap_key_data) and \
                ("0xffffffffffffffff" not in emap_key_data):
            # 16 bytes of BE_EMAP_KEY (footer) + 16 bytes of BE_EMAP_REC(header)

            rec_hdr_offset = emap_key[0][2]  #offset + 32
            emap_rec_data, _ = self.ReadCompleteRecord(rec_hdr_offset)
            # Skip key CRC
            emap_rec_data_full, _ = self.ReadCompleteRecordIncCRC(rec_hdr_offset)
            # Check er_cs_nob and if it is not 0 then go and corrupt last checksum 8 bytes
            if emap_rec_data[5] != "0x0":
                print("** Metadata key at offset {},"
                            " BE_EMAP_KEY ek_prefix = {}:{},"
                            " ek_offset = {}".format(offset - 24,
                                                        emap_key_data[0], emap_key_data[1],
                                                        emap_key_data[2]))
                print("** Metadata val at offset {},"
                            " BE_EMAP_REC er_start = {},"
                            " er_value = {}, er_unit_size = {},"
                            " er_cs_nob = {}, checksum = {}".format(
                    rec_hdr_offset, emap_rec_data[2],
                    emap_rec_data[3], emap_rec_data[4],
                    emap_rec_data[5], emap_rec_data[6:]))
                print("** Full Record before edit offset {},"
                            " BE_EMAP_REC hd_magic = {},"
                            " hd_bits = {}, er_start = {},"
                            " er_value = {}, er_unit_sz = {},"
                            " er_cksm_nob = {}, checksum = {},{},{},{}"
                            " footer = {}, CRC = {}"
                            .format(offset, emap_rec_data_full[0],
                                    emap_rec_data_full[1], emap_rec_data_full[2],
                                    emap_rec_data_full[3], emap_rec_data_full[4],
                                    emap_rec_data_full[5], emap_rec_data_full[6],
                                    emap_rec_data_full[7], emap_rec_data_full[8],
                                    emap_rec_data_full[9], emap_rec_data_full[10],
                                    emap_rec_data_full[11]))
                self.EditEmapMetadata(emap_rec_data_full, rec_hdr_offset, rec_hdr_offset + 84 + round(int(emap_rec_data_full[5], 16) / 8))
                print("** Full Record after edit offset {},"
                            " BE_EMAP_REC hd_magic = {},"
                            " hd_bits = {}, er_start = {},"
                            " er_value = {}, er_unit_sz = {},"
                            " er_cksm_nob = {}, checksum = {},{},{},{}"
                            " footer = {}, CRC = {}"
                            .format(offset, emap_rec_data_full[0],
                                    emap_rec_data_full[1], emap_rec_data_full[2],
                                    emap_rec_data_full[3], emap_rec_data_full[4],
                                    emap_rec_data_full[5], emap_rec_data_full[6],
                                    emap_rec_data_full[7], emap_rec_data_full[8],
                                    emap_rec_data_full[9], emap_rec_data_full[10],
                                    emap_rec_data_full[11]))
                emap_rec_data, _ = self.ReadCompleteRecord(rec_hdr_offset)
                count = count + 1

        return count

    # emap_key_list = [key_index, node_start_offset, emap_key_offset, node_length, key_size, value_offset]

    def ListAllEmapPerDevice(self):
        #print("*****Listing all emap keys and emap records with device id*****")
        count = 0
        emap_key_per_device = []
        node_offsets = m0_btree_types_dict["M0_BT_EMAP_EM_MAPPING"]
        for node_offset in node_offsets:
            emap_key_dict = self.emap_key_parser(node_offset)
        #print("emap_key_dict:{}".format(self.emap_key_dict))
        for key in emap_key_dict:
            values = emap_key_dict[key]
            #print(f"VALUES: {values}")
            for emap_key_list in values:
                #print(f"emap_key_list: {emap_key_list}")
                key_offset = emap_key_list[2] + 16
                emap_key_data, _ = self.ReadCompleteRecord(key_offset)
                stob_f_container_hex = emap_key_data[0]
                stob_f_key_hex = emap_key_data[1]
                _, _, device_id = self.ConvertAdstob2Cob(stob_f_container_hex, stob_f_key_hex)
                #print(f"==emap_key_list: {emap_key_list}")
                #print("==emap_key_data: {}".format(emap_key_data))
                if emap_key_data[2] != '0xffffffffffffffff':
                    #Jump to Record using offsets
                    rec_hdr_offset = emap_key_list[1] + emap_key_list[3] - emap_key_list[-1]
                    emap_key_per_device.append([count, key_offset, rec_hdr_offset, stob_f_container_hex, stob_f_key_hex])
                    
                    emap_rec_data_full, _ = self.ReadCompleteRecordIncCRC(rec_hdr_offset)
                    #print("==EMAP key per device: {}".format(emap_key_per_device))
                    #print("==emap_rec_data_full: {}".format(emap_rec_data_full))
                    if len(emap_rec_data_full) > 4 and emap_rec_data_full[4] != '0000000000000000':
                        print("=============[ Count :", count, " Key offset : ", key_offset, " Val offset : ",
                                rec_hdr_offset, "]==============")
                        print("** Metadata key"
                                    " BE_EMAP_KEY ek_prefix = {}:{},"
                                    " ek_offset = {}, Device ID = {}".format(
                            emap_key_data[0], emap_key_data[1], emap_key_data[2], device_id))
                        print("** Metadata val"
                                    " BE_EMAP_REC er_start = 0x{},"
                                    " er_value = 0x{}, er_unit_size = 0x{},"
                                    " er_cs_nob = 0x{}"
                                    .format(emap_rec_data_full[2],
                                            emap_rec_data_full[3], emap_rec_data_full[4],
                                            emap_rec_data_full[5]))
                        if emap_rec_data_full[5] != '0000000000000000':
                            cksum_count = round(int(emap_rec_data_full[5], 16) / 8)
                            print("Checksum : ", end=" ")
                            for i in range(cksum_count):
                                print("0x{}".format(emap_rec_data_full[6 + i]), end=" ")
                            comp_crc = self.ComputeCRC(emap_rec_data_full, len(emap_rec_data_full) - 2)
                            print("** Additional Record Data"
                                        " BE_EMAP_REC hd_magic = 0x{},"
                                        " hd_bits = 0x{}, footer = 0x{}, CRC = 0x{},"
                                        " Computed CRC = {}"
                                        .format(emap_rec_data_full[0],
                                                emap_rec_data_full[1], emap_rec_data_full[-2],
                                                emap_rec_data_full[-1], "0x{:016x}".format(comp_crc)))
                            if emap_rec_data_full[-1] != "0x{:016x}".format(comp_crc)[2:]:
                                print("**** Computed CRC Missmatch ****")
                            print()
                        count = count + 1
        return emap_key_per_device
