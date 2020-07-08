import typing as t
from fix.utils.enum import BaseStrEnum


class FixTag(BaseStrEnum):
    BeginSeqNo = "7"
    BeginString = "8"
    BodyLength = "9"
    CheckSum = "10"
    EndSeqNo = "16"
    MsgSeqNum = "34"
    MsgType = "35"
    NewSeqNo = "36"
    PossDupFlag = "43"
    RefSeqNum = "45"
    SenderCompID = "49"
    SenderSubID = "50"
    SendingTime = "52"
    TargetCompID = "56"
    TargetSubID = "57"
    Text = "58"
    Signature = "89"
    SecureDataLen = "90"
    SecureData = "91"
    SignatureLength = "93"
    RawDataLength = "95"
    RawData = "96"
    PossResend = "97"
    EncryptMethod = "98"
    HeartBtInt = "108"
    TestReqID = "112"
    OnBehalfOfCompID = "115"
    OnBehalfOfSubID = "116"
    OrigSendingTime = "122"
    GapFillFlag = "123"
    DeliverToCompID = "128"
    DeliverToSubID = "129"
    ResetSeqNumFlag = "141"
    SenderLocationID = "142"
    TargetLocationID = "143"
    OnBehalfOfLocationID = "144"
    DeliverToLocationID = "145"
    XmlDataLen = "212"
    XmlData = "213"
    MessageEncoding = "347"
    EncodedTextLen = "354"
    EncodedText = "355"
    LastMsgSeqNumProcessed = "369"
    RefTagID = "371"
    RefMsgType = "372"
    SessionRejectReason = "373"
    MaxMessageSize = "383"
    NoMsgTypes = "384"
    MsgDirection = "385"
    TestMessageIndicator = "464"
    Username = "553"
    Password = "554"
    NoHops = "627"
    HopCompID = "628"
    HopSendingTime = "629"
    HopRefID = "630"
    NextExpectedMsgSeqNum = "789"
    ApplVerID = "1128"
    CstmApplVerID = "1129"
    RefApplVerID = "1130"
    RefCstmApplVerID = "1131"
    DefaultApplVerID = "1137"


FT = FixTag


TYPE_MAP: t.Dict[str, str] = {
    FT.BeginSeqNo: "SEQNUM",
    FT.BeginString: "STRING",
    FT.BodyLength: "LENGTH",
    FT.CheckSum: "STRING",
    FT.EndSeqNo: "SEQNUM",
    FT.MsgSeqNum: "SEQNUM",
    FT.MsgType: "STRING",
    FT.NewSeqNo: "SEQNUM",
    FT.PossDupFlag: "BOOLEAN",
    FT.RefSeqNum: "SEQNUM",
    FT.SenderCompID: "STRING",
    FT.SenderSubID: "STRING",
    FT.SendingTime: "UTCTIMESTAMP",
    FT.TargetCompID: "STRING",
    FT.TargetSubID: "STRING",
    FT.Text: "STRING",
    FT.Signature: "DATA",
    FT.SecureDataLen: "LENGTH",
    FT.SecureData: "DATA",
    FT.SignatureLength: "LENGTH",
    FT.RawDataLength: "LENGTH",
    FT.RawData: "DATA",
    FT.PossResend: "BOOLEAN",
    FT.EncryptMethod: "INT",
    FT.HeartBtInt: "INT",
    FT.TestReqID: "STRING",
    FT.OnBehalfOfCompID: "STRING",
    FT.OnBehalfOfSubID: "STRING",
    FT.OrigSendingTime: "UTCTIMESTAMP",
    FT.GapFillFlag: "BOOLEAN",
    FT.DeliverToCompID: "STRING",
    FT.DeliverToSubID: "STRING",
    FT.ResetSeqNumFlag: "BOOLEAN",
    FT.SenderLocationID: "STRING",
    FT.TargetLocationID: "STRING",
    FT.OnBehalfOfLocationID: "STRING",
    FT.DeliverToLocationID: "STRING",
    FT.XmlDataLen: "LENGTH",
    FT.XmlData: "DATA",
    FT.MessageEncoding: "STRING",
    FT.EncodedTextLen: "LENGTH",
    FT.EncodedText: "DATA",
    FT.LastMsgSeqNumProcessed: "SEQNUM",
    FT.RefTagID: "INT",
    FT.RefMsgType: "STRING",
    FT.SessionRejectReason: "INT",
    FT.MaxMessageSize: "LENGTH",
    FT.NoMsgTypes: "NUMINGROUP",
    FT.MsgDirection: "CHAR",
    FT.TestMessageIndicator: "BOOLEAN",
    FT.Username: "STRING",
    FT.Password: "STRING",
    FT.NoHops: "NUMINGROUP",
    FT.HopCompID: "STRING",
    FT.HopSendingTime: "UTCTIMESTAMP",
    FT.HopRefID: "SEQNUM",
    FT.NextExpectedMsgSeqNum: "SEQNUM",
    FT.ApplVerID: "STRING",
    FT.CstmApplVerID: "STRING",
    FT.RefApplVerID: "STRING",
    FT.RefCstmApplVerID: "STRING",
    FT.DefaultApplVerID: "STRING",
}
