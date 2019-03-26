import datetime as dt
import json

from dateutil import parser as dateparser
from iso3166 import countries, Country as _Country
from iso4217 import Currency as _Currency

from .constants import FixTag
from .utils.datetime import (
    fix_timestamp_from_date, timestring_from_date,
    datestring_from_date
)


__all__ = ('InvalidTypeError', 'Any', 'Bool',
           'Int', 'Float', 'String', 'Sequence', )


class InvalidTypeError(TypeError):
    pass


class Type:
    """Base Type that provides type coersion"""
    name = ''
    # Default value to be returned when initializing
    default = None
    # Types that do not need to be coerced
    expected_type = object
    # Types that are acceptable for coersion
    compatible_types = (str, )

    def _default(self):
        return self.default

    def load(self, value=None):
        if value is None:
            return self._default()
        if self.test(value):
            return value
        if self.test_compatible(value):
            rv = self._deserialize(value)
            # Make sure convert was able to do the right thing
            # and give us the type we were expecting
            if self.test(rv):
                return rv
        raise InvalidTypeError(
            '{!r} is not a valid {}'.format(value, repr(self)))

    def dumps(self, value=None):
        if value is None:
            return self._serialize(self._default())
        if not self.test(value):
            value = self.load(value)
        rv = self._serialize(value)
        if not isinstance(rv, str):
            raise InvalidTypeError(
                '_serialize() did not return a str '
                'instead got {!r}'.format(value))
        return rv

    def _deserialize(self, value):
        return value

    def _serialize(self, value):
        return str(value)

    def test(self, value):
        """Check if the value is the correct type or not"""
        return isinstance(value, self.expected_type)

    def test_compatible(self, value):
        return isinstance(value, self.compatible_types)

    def __repr__(self):
        return self.name


class AnyType(Type):
    name = 'any'
    expected_type = object
    compatible_types = (object, )


class BoolType(Type):
    name = 'boolean'
    default = False
    expected_type = bool
    compatible_types = (str, int)

    def _deserialize(self, value):
        if isinstance(value, int):
            return bool(value)
        if value in ('y', 'Y', 'yes', 't', 'T', 'true', '1', 'on'):
            return True
        if value in ('n', 'N', 'no', 'f', 'F', 'false', '0', 'off'):
            return False

    def _serialize(self, value):
        if value is True:
            return 'Y'
        if value is False:
            return 'N'


class IntType(Type):
    name = 'integer'
    default = 0
    expected_type = int

    def _deserialize(self, value):
        try:
            return int(value)
        except ValueError:
            return


class PositiveIntType(IntType):
    name = 'positive integer'

    def test(self, value):
        if not super().test(value):
            return False
        if value < 0:
            return False
        return True


class DayOfMonthType(PositiveIntType):
    name = 'day of month'
    default = 1
    expected_type = int

    def test(self, value):
        if not super().test(value):
            return False
        return value in range(1, 32)


class FloatType(Type):
    name = 'float'
    default = 0.0
    expected_type = float
    compatible_types = (float, str, int)

    def _deserialize(self, value):
        try:
            return float(value)
        except ValueError:
            return


class CharType(Type):
    name = 'char'
    default = '\0'
    expected_type = str

    def test(self, value):
        if not super().test(value):
            return False
        if not len(value) == 1:
            return False
        return True


class StringType(Type):
    name = 'string'
    default = ''
    expected_type = str
    compatible_types = str


class MultipleValueStringType(Type):
    name = 'multiple value string'
    default = ''
    expected_type = tuple
    compatible_types = str

    def _deserialize(self, value):
        return tuple(value.split(' '))

    def _serialize(self, value):
        return ' '.join(value)


class CurrencyType(Type):
    name = 'currency'
    default = _Currency.usd.code
    expected_type = _Currency
    compatible_types = str

    def _deserialize(self, value):
        try:
            return _Currency(value)
        except ValueError as error:
            return

    def _serialize(self, value):
        return value.code


class CountryType(Type):
    name = 'country'
    default = countries.get('USA')
    expected_type = _Country
    compatible_types = str

    def test_compatible(self, value):
        if not super().test_compatible(value):
            return False
        return len(value) == 2

    def _deserialize(self, value):
        try:
            return countries.get(value)
        except KeyError as error:
            return

    def _serialize(self, value):
        return value.alpha2


class DatetimeType(Type):
    name = 'datetime'
    default = dt.datetime.utcnow()
    expected_type = dt.datetime
    compatible_types = str

    def _deserialize(self, value):
        try:
            return dateparser.parse(value)
        except ValueError:
            return

    def _serialize(self, value):
        return fix_timestamp_from_date(value)


class DateOnlyType(DatetimeType):

    def _serialize(self, value):
        return datestring_from_date(value)


class TimeOnlyType(DatetimeType):

    def _serialize(self, value):
        return timestring_from_date(value)


Data = AnyType()
Bool = BoolType()
Int = IntType()
PositiveInt = PositiveIntType()
Length = PositiveInt
NumberInGroup = PositiveInt
SeqNum = PositiveInt
TagNum = PositiveInt
DayOfMonth = DayOfMonthType()
Float = FloatType()
Quantity = FloatType()
Price = FloatType()
PriceOffset = FloatType()
Amount = FloatType()
Percentage = FloatType()
Char = CharType()
String = StringType()
Currency = CurrencyType()
Exchange = StringType()
MultipleValueString = MultipleValueStringType()
Country = CountryType()
UTCTimestamp = DatetimeType()
UTCDateOnly = DateOnlyType()
UTCTimeOnly = TimeOnlyType()
MonthYear = StringType()
LocalMarketDate = DatetimeType()


TAG_TYPEMAP = {
    FixTag.Account: String,
    FixTag.AdvId: String,
    FixTag.AdvRefID: String,
    FixTag.AdvSide: Char,
    FixTag.AdvTransType: String,
    FixTag.AvgPx: Price,
    FixTag.BeginSeqNo: SeqNum,
    FixTag.BeginString: String,
    FixTag.BodyLength: Length,
    FixTag.CheckSum: String,
    FixTag.ClOrdID: String,
    FixTag.Commission: Amount,
    FixTag.CommType: Char,
    FixTag.CumQty: Quantity,
    FixTag.Currency: Currency,
    FixTag.EndSeqNo: SeqNum,
    FixTag.ExecID: String,
    FixTag.ExecInst: MultipleValueString,
    FixTag.ExecRefID: String,
    FixTag.HandlInst: Char,
    FixTag.SecurityIDSource: String,
    FixTag.IOIID: String,
    FixTag.IOIQltyInd: Char,
    FixTag.IOIRefID: String,
    FixTag.IOIQty: String,
    FixTag.IOITransType: Char,
    FixTag.LastCapacity: Char,
    FixTag.LastMkt: Exchange,
    FixTag.LastPx: Price,
    FixTag.LastQty: Quantity,
    FixTag.NoLinesOfText: NumberInGroup,
    FixTag.MsgSeqNum: SeqNum,
    FixTag.MsgType: String,
    FixTag.NewSeqNo: SeqNum,
    FixTag.OrderID: String,
    FixTag.OrderQty: Quantity,
    FixTag.OrdStatus: Char,
    FixTag.OrdType: Char,
    FixTag.OrigClOrdID: String,
    FixTag.OrigTime: UTCTimestamp,
    FixTag.PossDupFlag: Bool,
    FixTag.Price: Price,
    FixTag.RefSeqNum: SeqNum,
    FixTag.SecurityID: String,
    FixTag.SenderCompID: String,
    FixTag.SenderSubID: String,
    FixTag.SendingTime: UTCTimestamp,
    FixTag.Quantity: Quantity,
    FixTag.Side: Char,
    FixTag.Symbol: String,
    FixTag.TargetCompID: String,
    FixTag.TargetSubID: String,
    FixTag.Text: String,
    FixTag.TimeInForce: Char,
    FixTag.TransactTime: UTCTimestamp,
    FixTag.Urgency: Char,
    FixTag.ValidUntilTime: UTCTimestamp,
    FixTag.SettlType: Char,
    FixTag.SettlDate: LocalMarketDate,
    FixTag.SymbolSfx: String,
    FixTag.ListID: String,
    FixTag.ListSeqNo: Int,
    FixTag.TotNoOrders: Int,
    FixTag.ListExecInst: String,
    FixTag.AllocID: String,
    FixTag.AllocTransType: Char,
    FixTag.RefAllocID: String,
    FixTag.NoOrders: NumberInGroup,
    FixTag.AvgPxPrecision: Int,
    FixTag.TradeDate: LocalMarketDate,
    FixTag.PositionEffect: Char,
    FixTag.NoAllocs: NumberInGroup,
    FixTag.AllocAccount: String,
    FixTag.AllocQty: Quantity,
    FixTag.ProcessCode: Char,
    FixTag.NoRpts: Int,
    FixTag.RptSeq: Int,
    FixTag.CxlQty: Quantity,
    FixTag.NoDlvyInst: NumberInGroup,
    FixTag.AllocStatus: Int,
    FixTag.AllocRejCode: Int,
    FixTag.Signature: Data,
    FixTag.SecureDataLen: Length,
    FixTag.SecureData: Data,
    FixTag.SignatureLength: Length,
    FixTag.EmailType: Char,
    FixTag.RawDataLength: Length,
    FixTag.RawData: Data,
    FixTag.PossResend: Bool,
    FixTag.EncryptMethod: Int,
    FixTag.StopPx: Price,
    FixTag.ExDestination: Exchange,
    FixTag.CxlRejReason: Int,
    FixTag.OrdRejReason: Int,
    FixTag.IOIQualifier: Char,
    FixTag.Issuer: String,
    FixTag.SecurityDesc: String,
    FixTag.HeartBtInt: Int,
    FixTag.MinQty: Quantity,
    FixTag.MaxFloor: Quantity,
    FixTag.TestReqID: String,
    FixTag.ReportToExch: Bool,
    FixTag.LocateReqd: Bool,
    FixTag.OnBehalfOfCompID: String,
    FixTag.OnBehalfOfSubID: String,
    FixTag.QuoteID: String,
    FixTag.NetMoney: Amount,
    FixTag.SettlCurrAmt: Amount,
    FixTag.SettlCurrency: Currency,
    FixTag.ForexReq: Bool,
    FixTag.OrigSendingTime: UTCTimestamp,
    FixTag.GapFillFlag: Bool,
    FixTag.NoExecs: NumberInGroup,
    FixTag.ExpireTime: UTCTimestamp,
    FixTag.DKReason: Char,
    FixTag.DeliverToCompID: String,
    FixTag.DeliverToSubID: String,
    FixTag.IOINaturalFlag: Bool,
    FixTag.QuoteReqID: String,
    FixTag.BidPx: Price,
    FixTag.OfferPx: Price,
    FixTag.BidSize: Quantity,
    FixTag.OfferSize: Quantity,
    FixTag.NoMiscFees: NumberInGroup,
    FixTag.MiscFeeAmt: Amount,
    FixTag.MiscFeeCurr: Currency,
    FixTag.MiscFeeType: Char,
    FixTag.PrevClosePx: Price,
    FixTag.ResetSeqNumFlag: Bool,
    FixTag.SenderLocationID: String,
    FixTag.TargetLocationID: String,
    FixTag.OnBehalfOfLocationID: String,
    FixTag.DeliverToLocationID: String,
    FixTag.NoRelatedSym: NumberInGroup,
    FixTag.Subject: String,
    FixTag.Headline: String,
    FixTag.URLLink: String,
    FixTag.ExecType: Char,
    FixTag.LeavesQty: Quantity,
    FixTag.CashOrderQty: Quantity,
    FixTag.AllocAvgPx: Price,
    FixTag.AllocNetMoney: Amount,
    FixTag.SettlCurrFxRate: Float,
    FixTag.SettlCurrFxRateCalc: Char,
    FixTag.NumDaysInterest: Int,
    FixTag.AccruedInterestRate: Percentage,
    FixTag.AccruedInterestAmt: Amount,
    FixTag.SettlInstMode: Char,
    FixTag.AllocText: String,
    FixTag.SettlInstID: String,
    FixTag.SettlInstTransType: Char,
    FixTag.EmailThreadID: String,
    FixTag.SettlInstSource: Char,
    FixTag.SecurityType: String,
    FixTag.EffectiveTime: UTCTimestamp,
    FixTag.StandInstDbType: Int,
    FixTag.StandInstDbName: String,
    FixTag.StandInstDbID: String,
    FixTag.SettlDeliveryType: Int,
    FixTag.BidSpotRate: Price,
    FixTag.BidForwardPoints: PriceOffset,
    FixTag.OfferSpotRate: Price,
    FixTag.OfferForwardPoints: PriceOffset,
    FixTag.OrderQty2: Quantity,
    FixTag.SettlDate2: LocalMarketDate,
    FixTag.LastSpotRate: Price,
    FixTag.LastForwardPoints: PriceOffset,
    FixTag.AllocLinkID: String,
    FixTag.AllocLinkType: Int,
    FixTag.SecondaryOrderID: String,
    FixTag.NoIOIQualifiers: NumberInGroup,
    FixTag.MaturityMonthYear: MonthYear,
    FixTag.PutOrCall: Int,
    FixTag.StrikePrice: Price,
    FixTag.CoveredOrUncovered: Int,
    FixTag.OptAttribute: Char,
    FixTag.SecurityExchange: Exchange,
    FixTag.NotifyBrokerOfCredit: Bool,
    FixTag.AllocHandlInst: Int,
    FixTag.MaxShow: Quantity,
    FixTag.PegOffsetValue: Float,
    FixTag.XmlDataLen: Length,
    FixTag.XmlData: Data,
    FixTag.SettlInstRefID: String,
    FixTag.NoRoutingIDs: NumberInGroup,
    FixTag.RoutingType: Int,
    FixTag.RoutingID: String,
    FixTag.Spread: PriceOffset,
    FixTag.BenchmarkCurveCurrency: Currency,
    FixTag.BenchmarkCurveName: String,
    FixTag.BenchmarkCurvePoint: String,
    FixTag.CouponRate: Percentage,
    FixTag.CouponPaymentDate: LocalMarketDate,
    FixTag.IssueDate: LocalMarketDate,
    FixTag.RepurchaseTerm: Int,
    FixTag.RepurchaseRate: Percentage,
    FixTag.Factor: Float,
    FixTag.TradeOriginationDate: LocalMarketDate,
    FixTag.ExDate: LocalMarketDate,
    FixTag.ContractMultiplier: Float,
    FixTag.NoStipulations: NumberInGroup,
    FixTag.StipulationType: String,
    FixTag.StipulationValue: String,
    FixTag.YieldType: String,
    FixTag.Yield: Percentage,
    FixTag.TotalTakedown: Amount,
    FixTag.Concession: Amount,
    FixTag.RepoCollateralSecurityType: String,
    FixTag.RedemptionDate: LocalMarketDate,
    FixTag.UnderlyingCouponPaymentDate: LocalMarketDate,
    FixTag.UnderlyingIssueDate: LocalMarketDate,
    FixTag.UnderlyingRepoCollateralSecurityType: String,
    FixTag.UnderlyingRepurchaseTerm: Int,
    FixTag.UnderlyingRepurchaseRate: Percentage,
    FixTag.UnderlyingFactor: Float,
    FixTag.UnderlyingRedemptionDate: LocalMarketDate,
    FixTag.LegCouponPaymentDate: LocalMarketDate,
    FixTag.LegIssueDate: LocalMarketDate,
    FixTag.LegRepoCollateralSecurityType: String,
    FixTag.LegRepurchaseTerm: Int,
    FixTag.LegRepurchaseRate: Percentage,
    FixTag.LegFactor: Float,
    FixTag.LegRedemptionDate: LocalMarketDate,
    FixTag.CreditRating: String,
    FixTag.UnderlyingCreditRating: String,
    FixTag.LegCreditRating: String,
    FixTag.TradedFlatSwitch: Bool,
    FixTag.BasisFeatureDate: LocalMarketDate,
    FixTag.BasisFeaturePrice: Price,
    FixTag.MDReqID: String,
    FixTag.SubscriptionRequestType: Char,
    FixTag.MarketDepth: Int,
    FixTag.MDUpdateType: Int,
    FixTag.AggregatedBook: Bool,
    FixTag.NoMDEntryTypes: NumberInGroup,
    FixTag.NoMDEntries: NumberInGroup,
    FixTag.MDEntryType: Char,
    FixTag.MDEntryPx: Price,
    FixTag.MDEntrySize: Quantity,
    FixTag.MDEntryDate: UTCDateOnly,
    FixTag.MDEntryTime: UTCTimeOnly,
    FixTag.TickDirection: Char,
    FixTag.MDMkt: Exchange,
    FixTag.QuoteCondition: MultipleValueString,
    FixTag.TradeCondition: MultipleValueString,
    FixTag.MDEntryID: String,
    FixTag.MDUpdateAction: Char,
    FixTag.MDEntryRefID: String,
    FixTag.MDReqRejReason: Char,
    FixTag.MDEntryOriginator: String,
    FixTag.LocationID: String,
    FixTag.DeskID: String,
    FixTag.DeleteReason: Char,
    FixTag.OpenCloseSettlFlag: MultipleValueString,
    FixTag.SellerDays: Int,
    FixTag.MDEntryBuyer: String,
    FixTag.MDEntrySeller: String,
    FixTag.MDEntryPositionNo: Int,
    FixTag.FinancialStatus: MultipleValueString,
    FixTag.CorporateAction: MultipleValueString,
    FixTag.DefBidSize: Quantity,
    FixTag.DefOfferSize: Quantity,
    FixTag.NoQuoteEntries: NumberInGroup,
    FixTag.NoQuoteSets: NumberInGroup,
    FixTag.QuoteStatus: Int,
    FixTag.QuoteCancelType: Int,
    FixTag.QuoteEntryID: String,
    FixTag.QuoteRejectReason: Int,
    FixTag.QuoteResponseLevel: Int,
    FixTag.QuoteSetID: String,
    FixTag.QuoteRequestType: Int,
    FixTag.TotNoQuoteEntries: Int,
    FixTag.UnderlyingSecurityIDSource: String,
    FixTag.UnderlyingIssuer: String,
    FixTag.UnderlyingSecurityDesc: String,
    FixTag.UnderlyingSecurityExchange: Exchange,
    FixTag.UnderlyingSecurityID: String,
    FixTag.UnderlyingSecurityType: String,
    FixTag.UnderlyingSymbol: String,
    FixTag.UnderlyingSymbolSfx: String,
    FixTag.UnderlyingMaturityMonthYear: MonthYear,
    FixTag.UnderlyingPutOrCall: Int,
    FixTag.UnderlyingStrikePrice: Price,
    FixTag.UnderlyingOptAttribute: Char,
    FixTag.UnderlyingCurrency: Currency,
    FixTag.SecurityReqID: String,
    FixTag.SecurityRequestType: Int,
    FixTag.SecurityResponseID: String,
    FixTag.SecurityResponseType: Int,
    FixTag.SecurityStatusReqID: String,
    FixTag.UnsolicitedIndicator: Bool,
    FixTag.SecurityTradingStatus: Int,
    FixTag.HaltReason: Char,
    FixTag.InViewOfCommon: Bool,
    FixTag.DueToRelated: Bool,
    FixTag.BuyVolume: Quantity,
    FixTag.SellVolume: Quantity,
    FixTag.HighPx: Price,
    FixTag.LowPx: Price,
    FixTag.Adjustment: Int,
    FixTag.TradSesReqID: String,
    FixTag.TradingSessionID: String,
    FixTag.ContraTrader: String,
    FixTag.TradSesMethod: Int,
    FixTag.TradSesMode: Int,
    FixTag.TradSesStatus: Int,
    FixTag.TradSesStartTime: UTCTimestamp,
    FixTag.TradSesOpenTime: UTCTimestamp,
    FixTag.TradSesPreCloseTime: UTCTimestamp,
    FixTag.TradSesCloseTime: UTCTimestamp,
    FixTag.TradSesEndTime: UTCTimestamp,
    FixTag.NumberOfOrders: Int,
    FixTag.MessageEncoding: String,
    FixTag.EncodedIssuerLen: Length,
    FixTag.EncodedIssuer: Data,
    FixTag.EncodedSecurityDescLen: Length,
    FixTag.EncodedSecurityDesc: Data,
    FixTag.EncodedListExecInstLen: Length,
    FixTag.EncodedListExecInst: Data,
    FixTag.EncodedTextLen: Length,
    FixTag.EncodedText: Data,
    FixTag.EncodedSubjectLen: Length,
    FixTag.EncodedSubject: Data,
    FixTag.EncodedHeadlineLen: Length,
    FixTag.EncodedHeadline: Data,
    FixTag.EncodedAllocTextLen: Length,
    FixTag.EncodedAllocText: Data,
    FixTag.EncodedUnderlyingIssuerLen: Length,
    FixTag.EncodedUnderlyingIssuer: Data,
    FixTag.EncodedUnderlyingSecurityDescLen: Length,
    FixTag.EncodedUnderlyingSecurityDesc: Data,
    FixTag.AllocPrice: Price,
    FixTag.QuoteSetValidUntilTime: UTCTimestamp,
    FixTag.QuoteEntryRejectReason: Int,
    FixTag.LastMsgSeqNumProcessed: SeqNum,
    FixTag.RefTagID: Int,
    FixTag.RefMsgType: String,
    FixTag.SessionRejectReason: Int,
    FixTag.BidRequestTransType: Char,
    FixTag.ContraBroker: String,
    FixTag.ComplianceID: String,
    FixTag.SolicitedFlag: Bool,
    FixTag.ExecRestatementReason: Int,
    FixTag.BusinessRejectRefID: String,
    FixTag.BusinessRejectReason: Int,
    FixTag.GrossTradeAmt: Amount,
    FixTag.NoContraBrokers: NumberInGroup,
    FixTag.MaxMessageSize: Length,
    FixTag.NoMsgTypes: NumberInGroup,
    FixTag.MsgDirection: Char,
    FixTag.NoTradingSessions: NumberInGroup,
    FixTag.TotalVolumeTraded: Quantity,
    FixTag.DiscretionInst: Char,
    FixTag.DiscretionOffsetValue: Float,
    FixTag.BidID: String,
    FixTag.ClientBidID: String,
    FixTag.ListName: String,
    FixTag.TotNoRelatedSym: Int,
    FixTag.BidType: Int,
    FixTag.NumTickets: Int,
    FixTag.SideValue1: Amount,
    FixTag.SideValue2: Amount,
    FixTag.NoBidDescriptors: NumberInGroup,
    FixTag.BidDescriptorType: Int,
    FixTag.BidDescriptor: String,
    FixTag.SideValueInd: Int,
    FixTag.LiquidityPctLow: Percentage,
    FixTag.LiquidityPctHigh: Percentage,
    FixTag.LiquidityValue: Amount,
    FixTag.EFPTrackingError: Percentage,
    FixTag.FairValue: Amount,
    FixTag.OutsideIndexPct: Percentage,
    FixTag.ValueOfFutures: Amount,
    FixTag.LiquidityIndType: Int,
    FixTag.WtAverageLiquidity: Percentage,
    FixTag.ExchangeForPhysical: Bool,
    FixTag.OutMainCntryUIndex: Amount,
    FixTag.CrossPercent: Percentage,
    FixTag.ProgRptReqs: Int,
    FixTag.ProgPeriodInterval: Int,
    FixTag.IncTaxInd: Int,
    FixTag.NumBidders: Int,
    FixTag.BidTradeType: Char,
    FixTag.BasisPxType: Char,
    FixTag.NoBidComponents: NumberInGroup,
    FixTag.Country: Country,
    FixTag.TotNoStrikes: Int,
    FixTag.PriceType: Int,
    FixTag.DayOrderQty: Quantity,
    FixTag.DayCumQty: Quantity,
    FixTag.DayAvgPx: Price,
    FixTag.GTBookingInst: Int,
    FixTag.NoStrikes: NumberInGroup,
    FixTag.ListStatusType: Int,
    FixTag.NetGrossInd: Int,
    FixTag.ListOrderStatus: Int,
    FixTag.ExpireDate: LocalMarketDate,
    FixTag.ListExecInstType: Char,
    FixTag.CxlRejResponseTo: Char,
    FixTag.UnderlyingCouponRate: Percentage,
    FixTag.UnderlyingContractMultiplier: Float,
    FixTag.ContraTradeQty: Quantity,
    FixTag.ContraTradeTime: UTCTimestamp,
    FixTag.LiquidityNumSecurities: Int,
    FixTag.MultiLegReportingType: Char,
    FixTag.StrikeTime: UTCTimestamp,
    FixTag.ListStatusText: String,
    FixTag.EncodedListStatusTextLen: Length,
    FixTag.EncodedListStatusText: Data,
    FixTag.PartyIDSource: Char,
    FixTag.PartyID: String,
    FixTag.NetChgPrevDay: PriceOffset,
    FixTag.PartyRole: Int,
    FixTag.NoPartyIDs: NumberInGroup,
    FixTag.NoSecurityAltID: NumberInGroup,
    FixTag.SecurityAltID: String,
    FixTag.SecurityAltIDSource: String,
    FixTag.NoUnderlyingSecurityAltID: NumberInGroup,
    FixTag.UnderlyingSecurityAltID: String,
    FixTag.UnderlyingSecurityAltIDSource: String,
    FixTag.Product: Int,
    FixTag.CFICode: String,
    FixTag.UnderlyingProduct: Int,
    FixTag.UnderlyingCFICode: String,
    FixTag.TestMessageIndicator: Bool,
    FixTag.BookingRefID: String,
    FixTag.IndividualAllocID: String,
    FixTag.RoundingDirection: Char,
    FixTag.RoundingModulus: Float,
    FixTag.CountryOfIssue: Country,
    FixTag.StateOrProvinceOfIssue: String,
    FixTag.LocaleOfIssue: String,
    FixTag.NoRegistDtls: NumberInGroup,
    FixTag.MailingDtls: String,
    FixTag.InvestorCountryOfResidence: Country,
    FixTag.PaymentRef: String,
    FixTag.DistribPaymentMethod: Int,
    FixTag.CashDistribCurr: Currency,
    FixTag.CommCurrency: Currency,
    FixTag.CancellationRights: Char,
    FixTag.MoneyLaunderingStatus: Char,
    FixTag.MailingInst: String,
    FixTag.TransBkdTime: UTCTimestamp,
    FixTag.ExecPriceType: Char,
    FixTag.ExecPriceAdjustment: Float,
    FixTag.DateOfBirth: LocalMarketDate,
    FixTag.TradeReportTransType: Int,
    FixTag.CardHolderName: String,
    FixTag.CardNumber: String,
    FixTag.CardExpDate: LocalMarketDate,
    FixTag.CardIssNum: String,
    FixTag.PaymentMethod: Int,
    FixTag.RegistAcctType: String,
    FixTag.Designation: String,
    FixTag.TaxAdvantageType: Int,
    FixTag.RegistRejReasonText: String,
    FixTag.FundRenewWaiv: Char,
    FixTag.CashDistribAgentName: String,
    FixTag.CashDistribAgentCode: String,
    FixTag.CashDistribAgentAcctNumber: String,
    FixTag.CashDistribPayRef: String,
    FixTag.CashDistribAgentAcctName: String,
    FixTag.CardStartDate: LocalMarketDate,
    FixTag.PaymentDate: LocalMarketDate,
    FixTag.PaymentRemitterID: String,
    FixTag.RegistStatus: Char,
    FixTag.RegistRejReasonCode: Int,
    FixTag.RegistRefID: String,
    FixTag.RegistDtls: String,
    FixTag.NoDistribInsts: NumberInGroup,
    FixTag.RegistEmail: String,
    FixTag.DistribPercentage: Percentage,
    FixTag.RegistID: String,
    FixTag.RegistTransType: Char,
    FixTag.ExecValuationPoint: UTCTimestamp,
    FixTag.OrderPercent: Percentage,
    FixTag.OwnershipType: Char,
    FixTag.NoContAmts: NumberInGroup,
    FixTag.ContAmtType: Int,
    FixTag.ContAmtValue: Float,
    FixTag.ContAmtCurr: Currency,
    FixTag.OwnerType: Int,
    FixTag.PartySubID: String,
    FixTag.NestedPartyID: String,
    FixTag.NestedPartyIDSource: Char,
    FixTag.SecondaryClOrdID: String,
    FixTag.SecondaryExecID: String,
    FixTag.OrderCapacity: Char,
    FixTag.OrderRestrictions: MultipleValueString,
    FixTag.MassCancelRequestType: Char,
    FixTag.MassCancelResponse: Char,
    FixTag.MassCancelRejectReason: Char,
    FixTag.TotalAffectedOrders: Int,
    FixTag.NoAffectedOrders: NumberInGroup,
    FixTag.AffectedOrderID: String,
    FixTag.AffectedSecondaryOrderID: String,
    FixTag.QuoteType: Int,
    FixTag.NestedPartyRole: Int,
    FixTag.NoNestedPartyIDs: NumberInGroup,
    FixTag.TotalAccruedInterestAmt: Amount,
    FixTag.MaturityDate: LocalMarketDate,
    FixTag.UnderlyingMaturityDate: LocalMarketDate,
    FixTag.InstrRegistry: String,
    FixTag.CashMargin: Char,
    FixTag.NestedPartySubID: String,
    FixTag.Scope: MultipleValueString,
    FixTag.MDImplicitDelete: Bool,
    FixTag.CrossID: String,
    FixTag.CrossType: Int,
    FixTag.CrossPrioritization: Int,
    FixTag.OrigCrossID: String,
    FixTag.NoSides: NumberInGroup,
    FixTag.Username: String,
    FixTag.Password: String,
    FixTag.NoLegs: NumberInGroup,
    FixTag.LegCurrency: Currency,
    FixTag.TotNoSecurityTypes: Int,
    FixTag.NoSecurityTypes: NumberInGroup,
    FixTag.SecurityListRequestType: Int,
    FixTag.SecurityRequestResult: Int,
    FixTag.RoundLot: Quantity,
    FixTag.MinTradeVol: Quantity,
    FixTag.MultiLegRptTypeReq: Int,
    FixTag.LegPositionEffect: Char,
    FixTag.LegCoveredOrUncovered: Int,
    FixTag.LegPrice: Price,
    FixTag.TradSesStatusRejReason: Int,
    FixTag.TradeRequestID: String,
    FixTag.TradeRequestType: Int,
    FixTag.PreviouslyReported: Bool,
    FixTag.TradeReportID: String,
    FixTag.TradeReportRefID: String,
    FixTag.MatchStatus: Char,
    FixTag.MatchType: String,
    FixTag.OddLot: Bool,
    FixTag.NoClearingInstructions: NumberInGroup,
    FixTag.ClearingInstruction: Int,
    FixTag.TradeInputSource: String,
    FixTag.TradeInputDevice: String,
    FixTag.NoDates: NumberInGroup,
    FixTag.AccountType: Int,
    FixTag.CustOrderCapacity: Int,
    FixTag.ClOrdLinkID: String,
    FixTag.MassStatusReqID: String,
    FixTag.MassStatusReqType: Int,
    FixTag.OrigOrdModTime: UTCTimestamp,
    FixTag.LegSettlType: Char,
    FixTag.LegSettlDate: LocalMarketDate,
    FixTag.DayBookingInst: Char,
    FixTag.BookingUnit: Char,
    FixTag.PreallocMethod: Char,
    FixTag.UnderlyingCountryOfIssue: Country,
    FixTag.UnderlyingStateOrProvinceOfIssue: String,
    FixTag.UnderlyingLocaleOfIssue: String,
    FixTag.UnderlyingInstrRegistry: String,
    FixTag.LegCountryOfIssue: Country,
    FixTag.LegStateOrProvinceOfIssue: String,
    FixTag.LegLocaleOfIssue: String,
    FixTag.LegInstrRegistry: String,
    FixTag.LegSymbol: String,
    FixTag.LegSymbolSfx: String,
    FixTag.LegSecurityID: String,
    FixTag.LegSecurityIDSource: String,
    FixTag.NoLegSecurityAltID: NumberInGroup,
    FixTag.LegSecurityAltID: String,
    FixTag.LegSecurityAltIDSource: String,
    FixTag.LegProduct: Int,
    FixTag.LegCFICode: String,
    FixTag.LegSecurityType: String,
    FixTag.LegMaturityMonthYear: MonthYear,
    FixTag.LegMaturityDate: LocalMarketDate,
    FixTag.LegStrikePrice: Price,
    FixTag.LegOptAttribute: Char,
    FixTag.LegContractMultiplier: Float,
    FixTag.LegCouponRate: Percentage,
    FixTag.LegSecurityExchange: Exchange,
    FixTag.LegIssuer: String,
    FixTag.EncodedLegIssuerLen: Length,
    FixTag.EncodedLegIssuer: Data,
    FixTag.LegSecurityDesc: String,
    FixTag.EncodedLegSecurityDescLen: Length,
    FixTag.EncodedLegSecurityDesc: Data,
    FixTag.LegRatioQty: Float,
    FixTag.LegSide: Char,
    FixTag.TradingSessionSubID: String,
    FixTag.AllocType: Int,
    FixTag.NoHops: NumberInGroup,
    FixTag.HopCompID: String,
    FixTag.HopSendingTime: UTCTimestamp,
    FixTag.HopRefID: SeqNum,
    FixTag.MidPx: Price,
    FixTag.BidYield: Percentage,
    FixTag.MidYield: Percentage,
    FixTag.OfferYield: Percentage,
    FixTag.ClearingFeeIndicator: String,
    FixTag.WorkingIndicator: Bool,
    FixTag.LegLastPx: Price,
    FixTag.PriorityIndicator: Int,
    FixTag.PriceImprovement: PriceOffset,
    FixTag.Price2: Price,
    FixTag.LastForwardPoints2: PriceOffset,
    FixTag.BidForwardPoints2: PriceOffset,
    FixTag.OfferForwardPoints2: PriceOffset,
    FixTag.RFQReqID: String,
    FixTag.MktBidPx: Price,
    FixTag.MktOfferPx: Price,
    FixTag.MinBidSize: Quantity,
    FixTag.MinOfferSize: Quantity,
    FixTag.QuoteStatusReqID: String,
    FixTag.LegalConfirm: Bool,
    FixTag.UnderlyingLastPx: Price,
    FixTag.UnderlyingLastQty: Quantity,
    FixTag.LegRefID: String,
    FixTag.ContraLegRefID: String,
    FixTag.SettlCurrBidFxRate: Float,
    FixTag.SettlCurrOfferFxRate: Float,
    FixTag.QuoteRequestRejectReason: Int,
    FixTag.SideComplianceID: String,
    FixTag.AcctIDSource: Int,
    FixTag.AllocAcctIDSource: Int,
    FixTag.BenchmarkPrice: Price,
    FixTag.BenchmarkPriceType: Int,
    FixTag.ConfirmID: String,
    FixTag.ConfirmStatus: Int,
    FixTag.ConfirmTransType: Int,
    FixTag.ContractSettlMonth: MonthYear,
    FixTag.DeliveryForm: Int,
    FixTag.LastParPx: Price,
    FixTag.NoLegAllocs: NumberInGroup,
    FixTag.LegAllocAccount: String,
    FixTag.LegIndividualAllocID: String,
    FixTag.LegAllocQty: Quantity,
    FixTag.LegAllocAcctIDSource: String,
    FixTag.LegSettlCurrency: Currency,
    FixTag.LegBenchmarkCurveCurrency: Currency,
    FixTag.LegBenchmarkCurveName: String,
    FixTag.LegBenchmarkCurvePoint: String,
    FixTag.LegBenchmarkPrice: Price,
    FixTag.LegBenchmarkPriceType: Int,
    FixTag.LegBidPx: Price,
    FixTag.LegIOIQty: String,
    FixTag.NoLegStipulations: NumberInGroup,
    FixTag.LegOfferPx: Price,
    FixTag.LegPriceType: Int,
    FixTag.LegQty: Quantity,
    FixTag.LegStipulationType: String,
    FixTag.LegStipulationValue: String,
    FixTag.LegSwapType: Int,
    FixTag.Pool: String,
    FixTag.QuotePriceType: Int,
    FixTag.QuoteRespID: String,
    FixTag.QuoteRespType: Int,
    FixTag.QuoteQualifier: Char,
    FixTag.YieldRedemptionDate: LocalMarketDate,
    FixTag.YieldRedemptionPrice: Price,
    FixTag.YieldRedemptionPriceType: Int,
    FixTag.BenchmarkSecurityID: String,
    FixTag.ReversalIndicator: Bool,
    FixTag.YieldCalcDate: LocalMarketDate,
    FixTag.NoPositions: NumberInGroup,
    FixTag.PosType: String,
    FixTag.LongQty: Quantity,
    FixTag.ShortQty: Quantity,
    FixTag.PosQtyStatus: Int,
    FixTag.PosAmtType: String,
    FixTag.PosAmt: Amount,
    FixTag.PosTransType: Int,
    FixTag.PosReqID: String,
    FixTag.NoUnderlyings: NumberInGroup,
    FixTag.PosMaintAction: Int,
    FixTag.OrigPosReqRefID: String,
    FixTag.PosMaintRptRefID: String,
    FixTag.ClearingBusinessDate: LocalMarketDate,
    FixTag.SettlSessID: String,
    FixTag.SettlSessSubID: String,
    FixTag.AdjustmentType: Int,
    FixTag.ContraryInstructionIndicator: Bool,
    FixTag.PriorSpreadIndicator: Bool,
    FixTag.PosMaintRptID: String,
    FixTag.PosMaintStatus: Int,
    FixTag.PosMaintResult: Int,
    FixTag.PosReqType: Int,
    FixTag.ResponseTransportType: Int,
    FixTag.ResponseDestination: String,
    FixTag.TotalNumPosReports: Int,
    FixTag.PosReqResult: Int,
    FixTag.PosReqStatus: Int,
    FixTag.SettlPrice: Price,
    FixTag.SettlPriceType: Int,
    FixTag.UnderlyingSettlPrice: Price,
    FixTag.UnderlyingSettlPriceType: Int,
    FixTag.PriorSettlPrice: Price,
    FixTag.NoQuoteQualifiers: NumberInGroup,
    FixTag.AllocSettlCurrency: Currency,
    FixTag.AllocSettlCurrAmt: Amount,
    FixTag.InterestAtMaturity: Amount,
    FixTag.LegDatedDate: LocalMarketDate,
    FixTag.LegPool: String,
    FixTag.AllocInterestAtMaturity: Amount,
    FixTag.AllocAccruedInterestAmt: Amount,
    FixTag.DeliveryDate: LocalMarketDate,
    FixTag.AssignmentMethod: Char,
    FixTag.AssignmentUnit: Quantity,
    FixTag.OpenInterest: Amount,
    FixTag.ExerciseMethod: Char,
    FixTag.TotNumTradeReports: Int,
    FixTag.TradeRequestResult: Int,
    FixTag.TradeRequestStatus: Int,
    FixTag.TradeReportRejectReason: Int,
    FixTag.SideMultiLegReportingType: Int,
    FixTag.NoPosAmt: NumberInGroup,
    FixTag.AutoAcceptIndicator: Bool,
    FixTag.AllocReportID: String,
    FixTag.NoNested2PartyIDs: NumberInGroup,
    FixTag.Nested2PartyID: String,
    FixTag.Nested2PartyIDSource: Char,
    FixTag.Nested2PartyRole: Int,
    FixTag.Nested2PartySubID: String,
    FixTag.BenchmarkSecurityIDSource: String,
    FixTag.SecuritySubType: String,
    FixTag.UnderlyingSecuritySubType: String,
    FixTag.LegSecuritySubType: String,
    FixTag.AllowableOneSidednessPct: Percentage,
    FixTag.AllowableOneSidednessValue: Amount,
    FixTag.AllowableOneSidednessCurr: Currency,
    FixTag.NoTrdRegTimestamps: NumberInGroup,
    FixTag.TrdRegTimestamp: UTCTimestamp,
    FixTag.TrdRegTimestampType: Int,
    FixTag.TrdRegTimestampOrigin: String,
    FixTag.ConfirmRefID: String,
    FixTag.ConfirmType: Int,
    FixTag.ConfirmRejReason: Int,
    FixTag.BookingType: Int,
    FixTag.IndividualAllocRejCode: Int,
    FixTag.SettlInstMsgID: String,
    FixTag.NoSettlInst: NumberInGroup,
    FixTag.LastUpdateTime: UTCTimestamp,
    FixTag.AllocSettlInstType: Int,
    FixTag.NoSettlPartyIDs: NumberInGroup,
    FixTag.SettlPartyID: String,
    FixTag.SettlPartyIDSource: Char,
    FixTag.SettlPartyRole: Int,
    FixTag.SettlPartySubID: String,
    FixTag.SettlPartySubIDType: Int,
    FixTag.DlvyInstType: Char,
    FixTag.TerminationType: Int,
    FixTag.NextExpectedMsgSeqNum: SeqNum,
    FixTag.OrdStatusReqID: String,
    FixTag.SettlInstReqID: String,
    FixTag.SettlInstReqRejCode: Int,
    FixTag.SecondaryAllocID: String,
    FixTag.AllocReportType: Int,
    FixTag.AllocReportRefID: String,
    FixTag.AllocCancReplaceReason: Int,
    FixTag.CopyMsgIndicator: Bool,
    FixTag.AllocAccountType: Int,
    FixTag.OrderAvgPx: Price,
    FixTag.OrderBookingQty: Quantity,
    FixTag.NoSettlPartySubIDs: NumberInGroup,
    FixTag.NoPartySubIDs: NumberInGroup,
    FixTag.PartySubIDType: Int,
    FixTag.NoNestedPartySubIDs: NumberInGroup,
    FixTag.NestedPartySubIDType: Int,
    FixTag.NoNested2PartySubIDs: NumberInGroup,
    FixTag.Nested2PartySubIDType: Int,
    FixTag.AllocIntermedReqType: Int,
    FixTag.UnderlyingPx: Price,
    FixTag.PriceDelta: Float,
    FixTag.ApplQueueMax: Int,
    FixTag.ApplQueueDepth: Int,
    FixTag.ApplQueueResolution: Int,
    FixTag.ApplQueueAction: Int,
    FixTag.NoAltMDSource: NumberInGroup,
    FixTag.AltMDSourceID: String,
    FixTag.SecondaryTradeReportID: String,
    FixTag.AvgPxIndicator: Int,
    FixTag.TradeLinkID: String,
    FixTag.OrderInputDevice: String,
    FixTag.UnderlyingTradingSessionID: String,
    FixTag.UnderlyingTradingSessionSubID: String,
    FixTag.TradeLegRefID: String,
    FixTag.ExchangeRule: String,
    FixTag.TradeAllocIndicator: Int,
    FixTag.ExpirationCycle: Int,
    FixTag.TrdType: Int,
    FixTag.TrdSubType: Int,
    FixTag.TransferReason: String,
    FixTag.TotNumAssignmentReports: Int,
    FixTag.AsgnRptID: String,
    FixTag.ThresholdAmount: PriceOffset,
    FixTag.PegMoveType: Int,
    FixTag.PegOffsetType: Int,
    FixTag.PegLimitType: Int,
    FixTag.PegRoundDirection: Int,
    FixTag.PeggedPrice: Price,
    FixTag.PegScope: Int,
    FixTag.DiscretionMoveType: Int,
    FixTag.DiscretionOffsetType: Int,
    FixTag.DiscretionLimitType: Int,
    FixTag.DiscretionRoundDirection: Int,
    FixTag.DiscretionPrice: Price,
    FixTag.DiscretionScope: Int,
    FixTag.TargetStrategy: Int,
    FixTag.TargetStrategyParameters: String,
    FixTag.ParticipationRate: Percentage,
    FixTag.TargetStrategyPerformance: Float,
    FixTag.LastLiquidityInd: Int,
    FixTag.PublishTrdIndicator: Bool,
    FixTag.ShortSaleReason: Int,
    FixTag.QtyType: Int,
    FixTag.SecondaryTrdType: Int,
    FixTag.TradeReportType: Int,
    FixTag.AllocNoOrdersType: Int,
    FixTag.SharedCommission: Amount,
    FixTag.ConfirmReqID: String,
    FixTag.AvgParPx: Price,
    FixTag.ReportedPx: Price,
    FixTag.NoCapacities: NumberInGroup,
    FixTag.OrderCapacityQty: Quantity,
    FixTag.NoEvents: NumberInGroup,
    FixTag.EventType: Int,
    FixTag.EventDate: LocalMarketDate,
    FixTag.EventPx: Price,
    FixTag.EventText: String,
    FixTag.PctAtRisk: Percentage,
    FixTag.NoInstrAttrib: NumberInGroup,
    FixTag.InstrAttribType: Int,
    FixTag.InstrAttribValue: String,
    FixTag.DatedDate: LocalMarketDate,
    FixTag.InterestAccrualDate: LocalMarketDate,
    FixTag.CPProgram: Int,
    FixTag.CPRegType: String,
    FixTag.UnderlyingCPProgram: String,
    FixTag.UnderlyingCPRegType: String,
    FixTag.UnderlyingQty: Quantity,
    FixTag.TrdMatchID: String,
    FixTag.SecondaryTradeReportRefID: String,
    FixTag.UnderlyingDirtyPrice: Price,
    FixTag.UnderlyingEndPrice: Price,
    FixTag.UnderlyingStartValue: Amount,
    FixTag.UnderlyingCurrentValue: Amount,
    FixTag.UnderlyingEndValue: Amount,
    FixTag.NoUnderlyingStips: NumberInGroup,
    FixTag.UnderlyingStipType: String,
    FixTag.UnderlyingStipValue: String,
    FixTag.MaturityNetMoney: Amount,
    FixTag.MiscFeeBasis: Int,
    FixTag.TotNoAllocs: Int,
    FixTag.LastFragment: Bool,
    FixTag.CollReqID: String,
    FixTag.CollAsgnReason: Int,
    FixTag.CollInquiryQualifier: Int,
    FixTag.NoTrades: NumberInGroup,
    FixTag.MarginRatio: Percentage,
    FixTag.MarginExcess: Amount,
    FixTag.TotalNetValue: Amount,
    FixTag.CashOutstanding: Amount,
    FixTag.CollAsgnID: String,
    FixTag.CollAsgnTransType: Int,
    FixTag.CollRespID: String,
    FixTag.CollAsgnRespType: Int,
    FixTag.CollAsgnRejectReason: Int,
    FixTag.CollAsgnRefID: String,
    FixTag.CollRptID: String,
    FixTag.CollInquiryID: String,
    FixTag.CollStatus: Int,
    FixTag.TotNumReports: Int,
    FixTag.LastRptRequested: Bool,
    FixTag.AgreementDesc: String,
    FixTag.AgreementID: String,
    FixTag.AgreementDate: LocalMarketDate,
    FixTag.StartDate: LocalMarketDate,
    FixTag.EndDate: LocalMarketDate,
    FixTag.AgreementCurrency: Currency,
    FixTag.DeliveryType: Int,
    FixTag.EndAccruedInterestAmt: Amount,
    FixTag.StartCash: Amount,
    FixTag.EndCash: Amount,
    FixTag.UserRequestID: String,
    FixTag.UserRequestType: Int,
    FixTag.NewPassword: String,
    FixTag.UserStatus: Int,
    FixTag.UserStatusText: String,
    FixTag.StatusValue: Int,
    FixTag.StatusText: String,
    FixTag.RefCompID: String,
    FixTag.RefSubID: String,
    FixTag.NetworkResponseID: String,
    FixTag.NetworkRequestID: String,
    FixTag.LastNetworkResponseID: String,
    FixTag.NetworkRequestType: Int,
    FixTag.NoCompIDs: NumberInGroup,
    FixTag.NetworkStatusResponseType: Int,
    FixTag.NoCollInquiryQualifier: NumberInGroup,
    FixTag.TrdRptStatus: Int,
    FixTag.AffirmStatus: Int,
    FixTag.UnderlyingStrikeCurrency: Currency,
    FixTag.LegStrikeCurrency: Currency,
    FixTag.TimeBracket: String,
    FixTag.CollAction: Int,
    FixTag.CollInquiryStatus: Int,
    FixTag.CollInquiryResult: Int,
    FixTag.StrikeCurrency: Currency,
    FixTag.NoNested3PartyIDs: NumberInGroup,
    FixTag.Nested3PartyID: String,
    FixTag.Nested3PartyIDSource: Char,
    FixTag.Nested3PartyRole: Int,
    FixTag.NoNested3PartySubIDs: NumberInGroup,
    FixTag.Nested3PartySubID: String,
    FixTag.Nested3PartySubIDType: Int,
    FixTag.LegContractSettlMonth: MonthYear,
    FixTag.LegInterestAccrualDate: LocalMarketDate,
}
