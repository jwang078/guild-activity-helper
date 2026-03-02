/**
 * Extracted logic for Hypixel SkyBlock Dungeon Class Average 50
 */

const test = require('node:test');
const assert = require('node:assert');

// These are the expected values given the max stats i think
// const CLASS_XP_PER_RUN = 504_001;
// const CLASS_XP_PER_RUN_MAIN_CLASS = 420_000;



function calculateRunsToCA50(playerXps, {
    targetXp = 569809640, floorName = "m7", hecatombLevel = "x",
    classBoosts = { archer: 1.1, berserk: 1.1, healer: 1.1, mage: 1.1, tank: 1.1 },
    grimoireLevel = "grimoire", scarfShard = 1.2, globalBoost = 1.0, mayor = 1.0
} = {}) {
    const FLOOR_XP = {
        m7: 300000, m6: 100000, m5: 70000, m4: 55000, m3: 35000, m2: 20000, m1: 15000,
        f7: 28000,  f6: 4880,   f5: 2400,  f4: 1420,  f3: 560,   f2: 220,   f1: 110,  entrance: 55,
    };
    const HECATOMB_XP = {
        x: 1.02, ix: 1.0184, viii: 1.0168, vii: 1.0152, vi: 1.0136,
        v: 1.012, iv: 1.0104, iii: 1.0088, ii: 1.0072, i: 1.0056, 0: 1.0,
    };
    const GRIMOIRE_XP = { grimoire: 1.06, thesis: 1.04, studies: 1.02, none: 1.0 };

    // 1. Define XP per run for each class based on boosts
    const floorValue = FLOOR_XP[floorName.toLowerCase()];
    const hecatomb = HECATOMB_XP[hecatombLevel.toLowerCase()];
    const grimoire = GRIMOIRE_XP[grimoireLevel.toLowerCase()];
    const classPerRun = Object.fromEntries(
        Object.keys(classBoosts).map(name => [
            name, floorValue * ((1 + (hecatomb - 1) * 2 + (classBoosts[name] - 1) + (grimoire - 1) + (scarfShard - 1) + (globalBoost - 1)) * Math.min(1.5, mayor))
        ])
    );

    // 2. Calculate XP left for each class
    const classNames = Object.keys(classPerRun);
    const classXpsLeft = Object.fromEntries(
        classNames.map(name => [name, Math.max(targetXp - playerXps[name], 0)])
    );

    const runsToCA50 = Object.fromEntries(classNames.map(name => [name, 0]));

    // 3. The Core Loop: Simulates runs by always playing the "lowest" class
    while (true) {
        if (Object.values(classXpsLeft).every(xp => xp <= 0)) break;

        const targetClass = classNames.reduce((max, name) => classXpsLeft[name] > classXpsLeft[max] ? name : max);

        // Apply XP to all classes for one run
        classNames.forEach(name => {
            const isTarget = name === targetClass;
            classXpsLeft[name] -= classPerRun[name] / (isTarget ? 1 : 4);
            if (isTarget) runsToCA50[name]++;
        });
    }

    return {
        classPerRun,
        breakdown: runsToCA50,
        total: Object.values(runsToCA50).reduce((a, b) => a + b, 0)
    };
}

function calculateCataRunsLeft(cataXp, {
    targetCataLevel = 50, floorName = "m7", hecatombLevel = "x",
    cataExpertRing = true, mayor = 1.0, globalBoost = 1.0,
} = {}) {
    const FLOOR_XP = {
        m7: 300000, m6: 100000, m5: 70000, m4: 55000, m3: 35000, m2: 20000, m1: 15000,
        f7: 28000,  f6: 4880,   f5: 2400,  f4: 1420,  f3: 560,   f2: 220,   f1: 110,  entrance: 55,
    };
    const HECATOMB_XP = {
        x: 1.02, ix: 1.0184, viii: 1.0168, vii: 1.0152, vi: 1.0136,
        v: 1.012, iv: 1.0104, iii: 1.0088, ii: 1.0072, i: 1.0056, 0: 1.0,
    };
    // Index 0 is amount of xp to go from cata level 0 to level 1
    // Index 49 is amount of xp to go from cata level 49 to level 50, etc
    const CATA_XP = [
        50, 75, 110, 160, 230, 330, 470, 670, 950, 1340, 1890, 2665, 3760, 5260, 7380, 10300,
        14400, 20000, 27600, 38000, 52500, 71500, 97000, 132000, 180000, 243000, 328000, 445000,
        600000, 800000, 1065000, 1410000, 1900000, 2500000, 3300000, 4300000, 5600000, 7200000,
        9200000, 12000000, 15000000, 19000000, 24000000, 30000000, 38000000, 48000000, 60000000,
        75000000, 93000000, 116250000, 200000000,
    ];

    const floorValue = FLOOR_XP[floorName.toLowerCase()];
    const hecatombDelta = HECATOMB_XP[hecatombLevel.toLowerCase()] - 1;

    // maxComps is the milestone completion cap for the floor, which affects cata XP scaling
    const maxComps = floorValue >= 15000 ? 26 : floorValue === 4880 ? 51 : 76;

    // Compute target cata XP
    let targetCataXp = 0;
    for (let i = 0; i < targetCataLevel; i++)
        // The amount of xp to level from 52 to 53, 53 to 54, etc are the same as 51 to 52
        targetCataXp += i < CATA_XP.length ? CATA_XP[i] : CATA_XP[-1];
    const cataXpLeft = Math.max(targetCataXp - cataXp, 0);

    // Compute cata XP per run (formula branches on expert ring + mayor)
    let cataPerRun;
    if (cataExpertRing && mayor > 1) {
        cataPerRun = floorValue * (0.95 + (mayor - 1) + (maxComps - 1) / 100 + 0.1 + hecatombDelta + (maxComps - 1) * (0.024 + hecatombDelta / 50));
    } else if (cataExpertRing) {
        cataPerRun = floorValue * (0.95 + 0.1 + hecatombDelta + (maxComps - 1) * (0.024 + hecatombDelta / 50));
    } else {
        cataPerRun = floorValue * (0.95 + hecatombDelta + (maxComps - 1) * (0.022 + hecatombDelta / 50));
    }
    cataPerRun = Math.ceil(cataPerRun * globalBoost);

    return {
        cataPerRun,
        runsLeft: Math.ceil(cataXpLeft / cataPerRun),
    };
}

/**
 * TEST SUITE / BENCHMARKING
 */
const scenarios = [
    {
        name: "Max Player (M7)",
        playerClassXps: { archer: 850e6, berserk: 950e6, healer: 750e6, mage: 750e6, tank: 750e6 },
        config: {},
        expectedTotalRuns: 0,
        expectedClassPerRun: { archer: 420000, berserk: 420000, healer: 420000, mage: 420000, tank: 420000 }
    },
    {
        name: "Near Max Player (M7)",
        playerClassXps: { archer: 550e6, berserk: 550e6, healer: 550e6, mage: 550e6, tank: 550e6 },
        config: {},
        expectedTotalRuns: 120,
        expectedClassPerRun: { archer: 420000, berserk: 420000, healer: 420000, mage: 420000, tank: 420000 }
    },
    {
        name: "Near Max Player with More Archer Xp (M7)",
        playerClassXps: { archer: 650e6, berserk: 550e6, healer: 550e6, mage: 550e6, tank: 550e6 },
        config: {},
        expectedTotalRuns: 108,
        expectedClassPerRun: { archer: 420000, berserk: 420000, healer: 420000, mage: 420000, tank: 420000 }
    },
    {
        name: "Fresh Level 0 (F7)",
        playerClassXps: { archer: 0, berserk: 0, healer: 0, mage: 0, tank: 0 },
        config: { floorName: "f7" },
        expectedTotalRuns: 36340,
        expectedClassPerRun: { archer: 39200, berserk: 39200, healer: 39200, mage: 39200, tank: 39200 }
    },
    {
        name: "Derpy Boost Test (M7)",
        playerClassXps: { archer: 200e6, berserk: 200e6, healer: 200e6, mage: 200e6, tank: 200e6 },
        config: { mayor: 1.5 },
        expectedTotalRuns: 1469,
        expectedClassPerRun: { archer: 630000, berserk: 630000, healer: 630000, mage: 630000, tank: 630000 }
    }
];

// Run the Benchmarks
scenarios.forEach(s => {
    test(s.name, () => {
        const result = calculateRunsToCA50(s.playerClassXps, s.config);
        
        console.log(`\n[${s.name}]`);
        console.log(`- Total Runs: ${result.total.toLocaleString()}`);
        console.log(`- Breakdown:`, result.breakdown)
        console.log(`- Class per Run:`, result.classPerRun)
        
        // Assertions to ensure logic isn't broken
        assert.strictEqual(result.total, s.expectedTotalRuns, `total: expected ${s.expectedTotalRuns}, got ${result.total}`);

        for (const [cls, xp] of Object.entries(s.expectedClassPerRun)) {
            const actual = Math.round(result.classPerRun[cls]);
            assert.strictEqual(actual, xp, `classPerRun.${cls}: expected ${xp}, got ${actual}`);
        }
    });
});
console.timeEnd("Total Benchmark Time");

const cataScenarios = [
    {
        name: "Cata: Already Max Player (M7)",
        cataXp: 950e6,
        config: {},
        expectedCataPerRun: 504001,
        expectedRunsLeft: 0,
    },
    {
        name: "Cata: Near Max Player (M7)",
        cataXp: 550e6,
        config: {},
        expectedCataPerRun: 504001,
        expectedRunsLeft: 40,
    },
    {
        name: "Cata: Fresh Level 0 (F7)",
        cataXp: 0,
        config: { floorName: "f7" },
        expectedCataPerRun: 47041,
        expectedRunsLeft: 12114,
    },
    {
        name: "Cata: Derpy Boost (M7)",
        cataXp: 200e6,
        config: { mayor: 1.5 },
        expectedCataPerRun: 729000,
        expectedRunsLeft: 508,
    },
    {
        name: "Cata: No Expert Ring (M7)",
        cataXp: 200e6,
        config: { cataExpertRing: false },
        expectedCataPerRun: 459000,
        expectedRunsLeft: 806,
    },
];

cataScenarios.forEach(s => {
    test(s.name, () => {
        const result = calculateCataRunsLeft(s.cataXp, s.config);

        console.log(`\n[${s.name}]`);
        console.log(`- Cata Per Run: ${result.cataPerRun.toLocaleString()}`);
        console.log(`- Runs Left: ${result.runsLeft.toLocaleString()}`);

        assert.strictEqual(result.cataPerRun, s.expectedCataPerRun, `cataPerRun: expected ${s.expectedCataPerRun}, got ${result.cataPerRun}`);
        assert.strictEqual(result.runsLeft,   s.expectedRunsLeft,   `runsLeft: expected ${s.expectedRunsLeft}, got ${result.runsLeft}`);
    });
});