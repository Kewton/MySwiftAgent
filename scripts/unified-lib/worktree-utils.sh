#!/bin/bash

# Worktree Utilities Library for MySwiftAgent
# Provides worktree detection and management functions

# Strict error handling (disabled for sourcing in tests)
# Individual functions handle their own errors appropriately

# Get the main repository path (worktree-aware)
# Returns the absolute path to the main repository
# Works in both regular repos and git worktrees
get_main_repo_path() {
    local git_common_dir
    git_common_dir=$(git rev-parse --git-common-dir 2>/dev/null || echo "")

    if [[ -n "$git_common_dir" ]] && [[ "$git_common_dir" != ".git" ]]; then
        # Worktree case (.git/worktrees/xxx)
        ( cd "$git_common_dir/.." && pwd )
    else
        # Regular repository case
        git rev-parse --show-toplevel 2>/dev/null || echo ""
    fi
}

# Check if current directory is a git worktree
# Returns 0 if worktree, 1 otherwise
is_worktree() {
    local git_common_dir
    git_common_dir=$(git rev-parse --git-common-dir 2>/dev/null || echo "")

    if [[ -n "$git_common_dir" ]] && [[ "$git_common_dir" != ".git" ]]; then
        return 0
    else
        return 1
    fi
}

# Get current worktree name
# Returns the basename of current directory
get_worktree_name() {
    basename "$(pwd)"
}

# List all worktrees with their paths
# Output format: "path branch"
# Uses git worktree list command
list_all_worktrees() {
    git worktree list --porcelain 2>/dev/null | awk '
        /^worktree / { path = substr($0, 10) }
        /^branch / { branch = substr($0, 8); print path, branch }
        /^detached$/ { print path, "(detached)" }
    '
}

# Get used worktree indices from .env.local files
# Scans all worktrees in the parent directory
# Returns array of used indices (space-separated)
get_used_worktree_indices() {
    local current_dir
    current_dir=$(pwd)
    local worktrees_dir
    worktrees_dir=$(dirname "$current_dir")

    local indices=()

    if [[ -d "$worktrees_dir" ]]; then
        for worktree in "$worktrees_dir"/*/; do
            if [[ -f "${worktree}.env.local" ]]; then
                # Extract WORKTREE_INDEX from .env.local
                local index
                index=$(grep "^WORKTREE_INDEX=" "${worktree}.env.local" 2>/dev/null | cut -d'=' -f2)
                if [[ -n "$index" ]] && [[ "$index" =~ ^[0-9]+$ ]]; then
                    indices+=("$index")
                fi
            fi
        done
    fi

    # Sort and deduplicate
    if [[ ${#indices[@]} -gt 0 ]]; then
        printf '%s\n' "${indices[@]}" | sort -n | uniq | tr '\n' ' '
    fi
}

# Find the next available worktree index
# Returns the smallest available index starting from 1
# Uses .env.local files to track assigned indices
find_available_worktree_index() {
    local used_indices_str
    used_indices_str=$(get_used_worktree_indices)

    # Convert space-separated string to array
    local used_indices=()
    if [[ -n "$used_indices_str" ]]; then
        read -ra used_indices <<< "$used_indices_str"
    fi

    # Find smallest available index starting from 1
    local index=1
    for used in "${used_indices[@]}"; do
        if [[ $index -eq $used ]]; then
            index=$((index + 1))
        else
            break
        fi
    done

    echo "$index"
}

# Get worktree index for current worktree
# If .env.local exists, read from it
# Otherwise, calculate and return next available index
get_current_worktree_index() {
    if [[ -f .env.local ]]; then
        local index
        index=$(grep "^WORKTREE_INDEX=" .env.local 2>/dev/null | cut -d'=' -f2)
        if [[ -n "$index" ]] && [[ "$index" =~ ^[0-9]+$ ]]; then
            echo "$index"
            return 0
        fi
    fi

    # If not found in .env.local, calculate next available
    find_available_worktree_index
}

# Get worktree information summary
# Returns formatted string with worktree details
get_worktree_info() {
    local worktree_name
    worktree_name=$(get_worktree_name)
    local worktree_index
    worktree_index=$(get_current_worktree_index)
    local main_repo
    main_repo=$(get_main_repo_path)

    cat <<EOF
Worktree Name: $worktree_name
Worktree Index: $worktree_index
Main Repository: $main_repo
Is Worktree: $(is_worktree && echo "Yes" || echo "No")
EOF
}

# Count total number of worktrees
# Returns the count as integer
count_worktrees() {
    git worktree list 2>/dev/null | wc -l | tr -d ' '
}

# Export functions for use in other scripts
export -f get_main_repo_path
export -f is_worktree
export -f get_worktree_name
export -f list_all_worktrees
export -f get_used_worktree_indices
export -f find_available_worktree_index
export -f get_current_worktree_index
export -f get_worktree_info
export -f count_worktrees
