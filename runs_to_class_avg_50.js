/**
 * Extracted logic for Hypixel SkyBlock Dungeon Class Average 50
 */

const test = require('node:test');
const assert = require('node:assert');

// These are the expected values given the max stats i think
// const CLASS_XP_PER_RUN = 504_001;
// const CLASS_XP_PER_RUN_MAIN_CLASS = 420_000;

// Constant XP table from the original script

function calculateRunsToCA50(playerXps, {
    targetXp = 569809640, floorValue = 300000, hecatomb = 1.02,
    classBoosts = { archer: 1.1, berserk: 1.1, healer: 1.1, mage: 1.1, tank: 1.1 },
    grimoire = 1.06, scarfShard = 1.2, globalBoost = 1.0, mayor = 1.0
} = {}) {
    // 1. Define XP per run for each class based on boosts
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

/**
 * TEST SUITE / BENCHMARKING
 */
const scenarios = [
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
        config: { floorValue: 28000 },
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
        assert.strictEqual(result.total, s.expectedTotalRuns, "Total runs mismatch");
        
        for (const [cls, xp] of Object.entries(s.expectedClassPerRun)) {
            assert.strictEqual(Math.round(result.classPerRun[cls]), xp, `classPerRun.${cls} mismatch`);
        }
    });
});
console.timeEnd("Total Benchmark Time");