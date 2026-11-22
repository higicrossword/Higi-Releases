package com.example.hebrewcrossword

fun main() {
    fun parsed(src:String) = AdminLocalOcrLengthV213.extract(src,
        mapOf(1 to 5,4 to 5,7 to 3,8 to 7,9 to 7,11 to 3,12 to 6,18 to 8,20 to 4),
        mapOf(1 to 5,2 to 7,3 to 3))
    val sample = """
        מאוזן: 1. הגדרה (5) 4. הגדרה (3,2)
        7. (עם 17 מאוזן) הגדרה (3,2) 8. הגדרה (7)
        11. (עם 19 מאונך) הגדרה (3,2) 12. הגדרה (6)
        18. הגדרה (3,5) 20. הגדרה (4)
        מאונך: 1. הגדרה (5) 2. הגדרה (7)
    """.trimIndent()
    val a=parsed(sample)
    for(n in listOf(4,7,11,18)) {
        check(a[AdminLocalOcrLengthV213.Key("across",n)] == if(n==18) listOf(3,5) else listOf(3,2))
    }
    check(parsed("מאוזן: 4. הגדרה (3,2) (2,3) מאונך: 1. הגדרה (5)").isEmpty())
    check(parsed("מאוזן: 4. הגדרה (4,2) מאונך: 1. הגדרה (5)").isEmpty())
    check(parsed("מאוזן: 7. הגדרה (2,3) 4. הגדרה (3,2) מאונך: 1. הגדרה (5)").isEmpty())
    check(parsed("מאוזן: 4. הגדרה (3,2)").isEmpty())
    println("V213_ADMIN_LOCAL_OCR_SYNTHETIC_QA_PASS")
}
