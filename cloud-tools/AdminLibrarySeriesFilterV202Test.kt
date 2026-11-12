package com.example.hebrewcrossword

import org.junit.Assert.*
import org.junit.Test

class AdminLibrarySeriesFilterV202Test {
    @Test fun optionsAreUniqueAndStable(){
        assertEquals(6,AdminLibrarySeriesFilterV202.options.size)
        assertEquals(6,AdminLibrarySeriesFilterV202.options.map{it.id}.toSet().size)
        assertEquals(AdminLibrarySeriesFilterV202.ALL,AdminLibrarySeriesFilterV202.normalized("unknown"))
    }
    @Test fun mondayAndWednesdayAreOneGroup(){
        val f=AdminLibrarySeriesFilterV202.YEDIOTH
        assertTrue(AdminLibrarySeriesFilterV202.matches(f,"YEDIOTH_MONDAY_DEKEL"))
        assertTrue(AdminLibrarySeriesFilterV202.matches(f,"YEDIOTH_WEDNESDAY_DEKEL"))
        assertFalse(AdminLibrarySeriesFilterV202.matches(f,"TARTEY_DEKEL"))
    }
    @Test fun seriesAreIndependentAndUnknownsStayInAll(){
        assertTrue(AdminLibrarySeriesFilterV202.matches(AdminLibrarySeriesFilterV202.ALL,null))
        for(s in listOf(AdminLibrarySeriesFilterV202.TARTEY,
            AdminLibrarySeriesFilterV202.HAFUCH,
            AdminLibrarySeriesFilterV202.MAARIV,
            AdminLibrarySeriesFilterV202.GUEST)){
            assertTrue(AdminLibrarySeriesFilterV202.matches(s,s))
            assertEquals(1,listOf(AdminLibrarySeriesFilterV202.TARTEY,
                AdminLibrarySeriesFilterV202.HAFUCH,
                AdminLibrarySeriesFilterV202.MAARIV,
                AdminLibrarySeriesFilterV202.GUEST).count { AdminLibrarySeriesFilterV202.matches(it,s) })
        }
    }
}