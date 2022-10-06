import base64
import hashlib
import logging
import random
import socket
import struct
import time
import xmltodict
from Crypto.Cipher import AES
from odoo import models, tools, api

logger = logging.getLogger(__name__)


class WorkwxCallback(models.AbstractModel):
    _name = 'workwx.callback'
    _description = '企业微信回调管理'

    def check_workwx_callback(self, **kwargs):
        """按企业微信要求回复明文验证回调地址"""
        token = tools.config.get('workwx_callback_token')
        content = [token, kwargs.get('timestamp', ''), kwargs.get('nonce', ''), kwargs.get('echostr', '')]
        content.sort()
        sha1 = hashlib.sha1(''.join(content).encode('utf-8'))
        dev_msg_signature = sha1.hexdigest()
        msg_signature = kwargs.get('msg_signature', '')
        # 密文哈希值校验
        if not msg_signature or dev_msg_signature != msg_signature:
            logger.warning(
                f'msg_signature校验失败:msg_signature={msg_signature};dev_msg_signature={dev_msg_signature};')
            return False
        # 密文解密
        try:
            key = base64.b64decode(tools.config.get('workwx_callback_aeskey') + "=")
            cipher = AES.new(key, AES.MODE_CBC, key[:16])
            rand_msg = cipher.decrypt(base64.b64decode(kwargs.get('echostr', '')))
            content = rand_msg[16:]  # 去掉前16随机字节
            msg_len = int.from_bytes(content[0:4], byteorder='big')  # 取出4字节的msg_len
            msg = content[4:msg_len + 4]  # 截取msg_len 长度的msg
            return msg.decode('utf-8')
        except Exception as e:
            logger.warning(f'密文解密失败:{str(e)};')
            return False

    def handle_workwx_callback(self, data, **kwargs):
        """处理企业微信回调"""
        # post请求的加密体是Encrypt,取出后替换为echostr可以复用校验方法获取明文
        xml_dict = xmltodict.parse(data).get('xml')
        kwargs.update({'echostr': xml_dict.get('Encrypt')})
        msg = self.check_workwx_callback(**kwargs)
        xml_dict = xmltodict.parse(msg).get('xml')
        callback_func = self.get_event_callback_func(xml_dict)
        if not callback_func:
            logger.exception(f'未找到对应的处理方法:{xml_dict}')
            return self.encrypt_workwx_message('failed')
        try:
            callback_func(xml_dict)
        except Exception as e:
            logger.exception(f'回调方法{callback_func.__name__}执行失败，{e}')
            return self.encrypt_workwx_message('failed')
        return self.encrypt_workwx_message('success')

    @api.model
    def get_event_callback_func(self, xml_dict):
        """根据不同参数执行回调方法"""
        return False

    def encrypt_workwx_message(self, message):
        """构造企业微信回调响应包"""
        Nonce = ''.join([random.choice('0123456789qwertyuiopasdfghjklzxcvbnm') for _ in range(16)])
        text = message.encode()
        receiveid = tools.config.get('workwx_corp_id')
        key = base64.b64decode(tools.config.get('workwx_callback_aeskey') + "=")
        # 拼接传输明文: 16随机字符串 + 4字节的text字节长度 + text + receiveid
        text = Nonce.encode() + struct.pack("I", socket.htonl(len(text))) + text + receiveid.encode()
        # 填充明文长度
        text = self.pkcs7_encoder(text)
        # 加密
        cryptor = AES.new(key, AES.MODE_CBC, key[:16])
        try:
            ciphertext = cryptor.encrypt(text)
            encrypt = base64.b64encode(ciphertext)
        except Exception as e:
            logger.warning(f'加密消息失败:{e}')
            return False
        msg_encrypt = encrypt.decode('utf8')
        # 生成安全签名
        try:
            token = tools.config.get('workwx_callback_token')
            timestamp = str(int(time.time()))
            sortlist = [token, timestamp, Nonce, msg_encrypt]
            sortlist.sort()
            sha = hashlib.sha1()
            sha.update("".join(sortlist).encode())
            msg_signaturet = sha.hexdigest()
        except Exception as e:
            logger.warning(f'加密消息-生成安全签名失败:{e}')
            return False
        # 组装xml消息
        return f"""<xml>
        <Encrypt><![CDATA[{msg_encrypt}]]></Encrypt>
        <MsgSignature><![CDATA[{msg_signaturet}]]></MsgSignature>
        <TimeStamp>{timestamp}</TimeStamp>
        <Nonce><![CDATA[{Nonce}]]></Nonce>
        </xml>"""

    def pkcs7_encoder(self, text, block_size=32):
        """pkcs7填充算法"""
        text_length = len(text)
        amount_to_pad = block_size - (text_length % block_size)
        if amount_to_pad == 0:
            amount_to_pad = block_size
        pad = chr(amount_to_pad)
        return text + (pad * amount_to_pad).encode()
