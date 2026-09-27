package com.swir.swirsms
import org.junit.Assert.*
import org.junit.Test

class CoreTest {
 @Test fun normalizeInternational() { assertEquals("+48123456789",PhoneRules.normalize("+48 (123) 456-789")) }
 @Test fun normalizeInternational00() { assertEquals("+4712345678",PhoneRules.normalize("0047 1234 5678")) }
 @Test fun preserveNational() { assertEquals("12345678",PhoneRules.normalize("12345678")) }
 @Test fun rejectLetters() { assertNull(PhoneRules.normalize("CALL12345678")) }
 @Test fun rejectUssd() { assertNull(PhoneRules.normalize("*21*123456789#")) }
 @Test fun rejectEmergency() { assertNull(PhoneRules.normalize("112")) }
 @Test fun rejectTooLong() { assertNull(PhoneRules.normalize("+1234567890123456")) }
 @Test fun rejectDoublePlus() { assertNull(PhoneRules.normalize("++4712345678")) }
 @Test fun rejectUrl() { assertNull(PhoneRules.normalize("https://123456789")) }
 @Test fun rejectEmpty() { assertNull(PhoneRules.normalize(" ")) }
 @Test fun deduplicateFormatting() { assertEquals(1,PhoneRules.unique(listOf(Recipient("A","+47 12345678"),Recipient("B","004712345678"))).size) }
 @Test fun gsm160() { assertEquals(1,SmsMath.stats("A".repeat(160)).segments) }
 @Test fun gsm161() { assertEquals(2,SmsMath.stats("A".repeat(161)).segments) }
 @Test fun gsm306() { assertEquals(2,SmsMath.stats("A".repeat(306)).segments) }
 @Test fun gsm307() { assertEquals(3,SmsMath.stats("A".repeat(307)).segments) }
 @Test fun extendedCost() { assertEquals(162,SmsMath.stats("^".repeat(81)).units); assertEquals(2,SmsMath.stats("^".repeat(81)).segments) }
 @Test fun formFeed() { assertEquals("GSM-7",SmsMath.stats("\u000c").encoding); assertEquals(2,SmsMath.stats("\u000c").units) }
 @Test fun unicode70() { assertEquals(1,SmsMath.stats("ą".repeat(70)).segments) }
 @Test fun unicode71() { assertEquals(2,SmsMath.stats("ą".repeat(71)).segments) }
 @Test fun unicode134() { assertEquals(2,SmsMath.stats("ą".repeat(134)).segments) }
 @Test fun emojiUsesTwoUnits() { assertEquals(72,SmsMath.stats("😊".repeat(36)).units); assertEquals(2,SmsMath.stats("😊".repeat(36)).segments) }
 @Test fun emptyHasNoSegments() { assertEquals(0,SmsMath.stats("").segments) }
 @Test fun sentNotDelivered() { assertEquals("SENT",ResultRules.state(2,2,0,0,0)) }
 @Test fun partialFailure() { assertEquals("PARTIAL",ResultRules.state(2,1,1,0,0)) }
 @Test fun failed() { assertEquals("FAILED",ResultRules.state(2,0,1,0,0)) }
 @Test fun delivered() { assertEquals("DELIVERED",ResultRules.state(2,2,0,2,0)) }
 @Test fun reportsCanArriveFirst() { assertEquals("DELIVERED",ResultRules.state(2,0,0,2,0)) }
 @Test fun singleReportNotAllDelivered() { assertEquals("SENT",ResultRules.state(2,2,0,1,0)) }
 @Test fun noCallbacksNotSent() { assertEquals("SENDING",ResultRules.state(1,0,0,0,0)) }
 @Test fun deliveryError() { assertEquals("DELIVERY_FAILED",ResultRules.state(1,1,0,0,1)) }
 @Test fun expiryBoundary() { assertFalse(ResultRules.expired(0,86_400_000)); assertTrue(ResultRules.expired(0,86_400_001)) }
}
