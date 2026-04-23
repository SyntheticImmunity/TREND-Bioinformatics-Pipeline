library(Rbowtie2)
library(Rsamtools)
library(dplyr)

setwd("./sam_files") # need to change accordingly
project_directory = '/n/scratch3/users/m/mw277/SP014/' # need to change accordingly

sample_files <- list.files(pattern="*.sam", full.names=T)
sample_name = strsplit(sample_files, '.fastq_trimmed.fastq')
sample_name_vector = character()
for (i in 1:length(sample_name)) {
  sample_name_vector <-append(sample_name_vector, substr(sample_name[[i]][1], start=3, stop=nchar(sample_name[[i]][1])))
}

sample_file_location_list <- setNames(as.list(sample_files),sample_name_vector)

#---make SAM into BAM---#
for (file_name in sample_file_location_list){
  asBam(file = paste0(project_directory, 'sam_files/', substr(file_name, 3, nchar(file_name))), overwrite = T)
}

#---extract counts---#
sample_files <- list.files(pattern="*.bam$", full.names=F)
sample_name = strsplit(sample_files, '.fastq_trimmed.fastq')
sample_name_vector = character()
for (i in 1:length(sample_name)) {
  sample_name_vector <-append(sample_name_vector, substr(sample_name[[i]][1], start=1, stop=nchar(sample_name[[i]][1])))
}

sample_file_location_list <- setNames(as.list(sample_files),sample_name_vector)

count_list <-list()
for (i in 1:length(sample_file_location_list)){
  count_list[[paste0(names(sample_file_location_list)[i])]] <- idxstatsBam(file = paste0(project_directory, 'sam_files/', sample_file_location_list[[i]]), overwrite = T)
}

barcode_counts <-data.frame(TFBS_random_bc = as.character(count_list[[names(sample_file_location_list)[1]]]$seqnames),stringsAsFactors = F)
for (name in names(sample_file_location_list)){
 barcode_counts[[name]]  <- as.numeric(count_list[[name]]$mapped)
}

barcode_counts_normalized <-data.frame(TFBS_random_bc = as.character(count_list[[names(sample_file_location_list)[1]]]$seqnames),stringsAsFactors = F)
for (name in names(sample_file_location_list)){
  barcode_counts_normalized[[name]]  <- as.numeric(count_list[[name]]$mapped*1000000/sum(count_list[[name]]$mapped))
}

#write code to save counts into
#---read library reference and form the complete result dataframe---#
setwd(project_directory)
Lib4_ref <- read.csv('./Lib4_info_concise_060621.csv', header = T, stringsAsFactors = F)
Lib4_NGS_result_unnormalized <- left_join(Lib4_ref, barcode_counts, by = 'TFBS_random_bc', sort=F)
Lib4_NGS_result_normalized <- left_join(Lib4_ref, barcode_counts_normalized, by = 'TFBS_random_bc', sort=F)

write.csv(Lib4_NGS_result_unnormalized, file='alignment_result_unnormalized_in_house_pipeline.csv', row.names = F)
write.csv(Lib4_NGS_result_normalized, file='alignment_result_normalized_in_house_pipeline.csv', row.names = F)

