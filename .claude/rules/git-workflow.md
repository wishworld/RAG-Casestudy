# Git Workflow Rules

**Environments:** `Local (laptop) -> Staging -> Prod`

**Promotion flow:** `feature/* -> staging -> prod`

```text
+-------------------+     +-----------+     +--------+
| Local (laptop)    | ->  |  staging  | ->  |  prod  |
| feature/* commits |     |  QA / UAT |     |  live  |
+-------------------+     +-----------+     +--------+
```

There is no `dev` branch. Your laptop IS the dev environment.
`staging` is the integration branch: all PRs land there.

## Branches

| Branch      | Purpose                                  |
|-------------|------------------------------------------|
| `prod`      | Production (live). Protected.            |
| `staging`   | Integration + QA / UAT. Protected.       |
| `feature/*` | Local work in progress. Cut from staging.|

## Starting a Feature
1. **Mandatory reverse sync** - merge `prod` into `staging` first if `staging` is behind
2. Create feature branch from `staging`: `feature/descriptive-name`
3. Commit with conventional messages (`feat:`, `fix:`, etc.)
4. **Mandatory pre-push sync** - merge latest `staging` into feature branch before pushing
5. Push feature branch, open PR to `staging`

## PR Flow
- PRs always target `staging` (never `prod` directly)
- After review approval, merge PR -> `staging`, delete feature branch

## Deploying to Staging
Merging the PR IS the staging deploy. To verify:
```
git checkout staging && git pull origin staging
```

## Deploying to Production
```
git checkout prod && git pull origin prod
git merge staging && git push origin prod
git tag -a vX.Y.Z -m "Release notes" && git push origin vX.Y.Z
```

## Staging Bugfix (found in QA, not yet in prod)
1. Branch from `staging`: `bugfix/description`
2. Fix, commit (`fix: description`), PR to `staging`
3. After merge, re-test staging

## Hotfix (live production bug)
1. Branch from `prod`: `hotfix/description`
2. Fix, commit (`hotfix: description`), merge to `prod`, push
3. **Mandatory backmerge** - merge `prod` into `staging`, push
4. Tag as patch release (`vX.Y.Z+1`), delete hotfix branch

## Daily Workflow
- **Morning:** switch to `staging`, pull latest, cut a feature branch
- **End of day:** must be on a feature branch - commit `wip: description` and push
- Never end the day with uncommitted changes on `staging` or `prod`
